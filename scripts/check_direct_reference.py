"""Verify blind excerpts against original PCM, never modify human annotations."""
import json
import sys
import wave
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.domain.minutes import content_digest

directory = ROOT/'output/direct-summary/reference-humaine'
annotation = directory/'annotations.json'
before = sha256_file(annotation)
pack = json.loads(annotation.read_text(encoding='utf-8'))
request = json.loads((ROOT/'output/information-registry/field-670/write.request.json').read_text(encoding='utf-8'))
assert pack['source_rows_sha256'] == content_digest(request['utterances'])
audio = Path(json.loads(request['utterances'][0]['source_json'])['normalized_audio'])
assert sha256_file(audio) == pack['audio_sha256']
clips = []
with wave.open(str(audio),'rb') as source:
    rate = source.getframerate()
    for item in pack['excerpts']:
        path = directory/item['audio']
        with wave.open(str(path),'rb') as clip:
            assert (clip.getnchannels(),clip.getsampwidth(),clip.getframerate()) == (
                source.getnchannels(),source.getsampwidth(),rate)
            source.setpos(round(item['start_ms']*rate/1000))
            expected = source.readframes(round((item['end_ms']-item['start_ms'])*rate/1000))
            assert clip.readframes(clip.getnframes()) == expected
            assert abs(clip.getnframes()/rate - 40.) < 1/rate
            clips.append({'id':item['id'],'seconds':clip.getnframes()/rate,'sha256':sha256_file(path)})
assert len(clips) == 12 and sha256_file(annotation) == before
report = {'scope':'byte-for-byte original PCM excerpt integrity; no semantic or speaker acceptance',
    'source_rows_sha256':pack['source_rows_sha256'],'audio_sha256':pack['audio_sha256'],
    'clips':clips,'total_seconds':sum(c['seconds'] for c in clips),'annotations_unchanged':True,
    'human_checked_excerpts':sum(e.get('human_checked') is True for e in pack['excerpts']),
    'quality_validated':False}
atomic_json(ROOT/'docs/evidence/direct-summary-human-reference.json',report)
print(json.dumps(report,ensure_ascii=True,indent=2))
