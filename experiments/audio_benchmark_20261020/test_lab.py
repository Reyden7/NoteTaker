import sys
import threading
import wave
import re
import pytest
from experiments.audio_benchmark_20261020.common import OUT,read,sha
from experiments.audio_benchmark_20261020.measured import run


def test_real_windows_job_counts_cpu_and_committed_memory(tmp_path):
    record=run([sys.executable,'-c','x=bytearray(8*1024**2); print(len(x))'],tmp_path/'normal',memory_limit=128*1024**2,timeout=20)
    assert record['status']=='completed' and record['exit_code']==0
    assert record['cpu']['user_seconds']+record['cpu']['kernel_seconds']>0
    assert 0<record['peak_job_committed_bytes']<=128*1024**2


def test_real_windows_memory_limit_rejects_allocations(tmp_path):
    code='import sys\nx=[]\ntry:\n for i in range(64): x.append(bytearray(8*1024**2))\nexcept MemoryError:\n print("EXPECTED_MEMORY_LIMIT",len(x)*8*1024**2,flush=True)\n sys.exit(23)\nsys.exit(24)\n'
    record=run([sys.executable,'-c',code],tmp_path/'quota',memory_limit=128*1024**2,timeout=20)
    assert record['status']=='failed' and record['exit_code']==23
    assert record['configured_job_memory_limit_bytes']==128*1024**2
    # PeakJobMemoryUsed is an observed accounting high-water mark, not the quota.
    # Verify the configured kernel quota AND actual denial before 128 MiB of payload.
    # The loop is bounded to 512 MiB so a broken limiter cannot exhaust host RAM.
    output=(tmp_path/'quota/stdout.txt').read_text().strip()
    assert output.startswith('EXPECTED_MEMORY_LIMIT ')
    allocated=int(output.split()[-1])
    assert 32*1024**2<=allocated<128*1024**2
    assert record['peak_job_committed_bytes']>0


def test_cancel_stops_owned_job_and_preserves_partial_files(tmp_path):
    cancel=tmp_path/'CANCEL'
    timer=threading.Timer(1,lambda:cancel.write_text('cancel'))
    timer.start()
    try: record=run([sys.executable,'-c','import time;print("started",flush=True);time.sleep(60)'],tmp_path/'cancelled',cancel=cancel,timeout=10)
    finally: timer.cancel()
    assert record['status']=='cancelled' and record['wall_seconds']<6
    assert 'started' in (tmp_path/'cancelled/stdout.txt').read_text()


def test_prepared_audio_is_exact_pcm_and_originals_unchanged():
    manifest=read(OUT/'manifest.json')
    with wave.open(manifest['source_audio'],'rb') as original:
        for label,case in manifest['cases'].items():
            with wave.open(case['audio'],'rb') as cropped:
                frames=cropped.getnframes();actual=cropped.readframes(frames)
                original.setpos(round(case['start_in_original_seconds']*16000))
                assert actual==original.readframes(frames)
                assert sha(case['audio'])==case['sha256']
    assert all(sha(p)==h for p,h in manifest['protected'].items())


@pytest.mark.parametrize('stage',['60s','180s','full'])
def test_real_whisperx_combination_keeps_all_recognized_text_and_marks_fallback(stage):
    """Covers the actual missing-space and wordless-segment adapter regressions."""
    compact=lambda s:re.sub(r'\s+','',s)
    raw=read(OUT/'runs/large-cuda-main'/stage/'result.json')['result']['segments']
    expected=compact(''.join(s['text'] for s in raw))
    folder=OUT/'combined/B-cuda'/stage
    stats=read(folder/'statistics.json')
    assert stats['recognized_text_preserved_ignoring_whitespace']
    for variant,summary in stats['variants'].items():
        result=read(folder/(variant+'.json'))
        rows=result['segments']
        assert compact(''.join(r['text'] for r in rows))==expected
        assert summary['combined_text_preserved_ignoring_whitespace']
        for index in result['unaligned_word_fallback_segment_indices']:
            matches=[r for r in rows if r['id']==f's{index}']
            assert len(matches)==1
            assert matches[0]['uncertain']
            assert matches[0]['source']['word_alignment_missing_or_incomplete']
        if variant.startswith('with-whisperx'):
            # Words are readable, not concatenated into e.g. "uneplateformeavec".
            for r in rows:
                spans=r['source'].get('word_spans',[])
                if len(spans)>1:
                    assert all(w['word'].startswith(' ') for w in spans)


def test_no_accuracy_is_inferred_from_unannotated_reference_or_group_counts():
    from experiments.audio_benchmark_20261020.analyze import describe
    stats=read(OUT/'combined/B-cuda/full/statistics.json')
    assert all(stats[k] is None for k in ('WER','DER','cpWER','cpCER'))
    assert stats['quality_validated'] is False
    rows=[{'start':0,'end':1,'speaker':'a'},{'start':0.5,'end':2,'speaker':'b'}]
    description=describe(rows,2)
    assert description['speaker_groups']==2
    assert description['speaker_group_count_is_accuracy'] is False
    assert describe([{'start':0,'end':1,'speaker':None}],2)['speaker_groups'] is None
