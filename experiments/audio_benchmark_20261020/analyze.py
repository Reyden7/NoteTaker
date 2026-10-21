"""Descriptive statistics; no accuracy inferred from group/fragment counts."""
import ast
import argparse
import statistics
from .common import ROOT,OUT,read,write


def align_reference(segments,diarization):
    # Execute only the two unchanged pure functions. No SessionStore/database import.
    path=ROOT/'src/notetaker/services/pipeline.py'
    tree=ast.parse(path.read_text(encoding='utf-8'))
    selected=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in {'lexical_words','align_transcript'}]
    if len(selected)!=2:raise ValueError('REFERENCE_FUNCTIONS_MISSING')
    space={};exec(compile(ast.Module(body=selected,type_ignores=[]),str(path),'exec'),space)
    return space['align_transcript'](segments,diarization)


def describe(rows,duration,*,has_text=False):
    lengths=[r['end']-r['start'] for r in rows]
    groups={r['speaker'] for r in rows if r.get('speaker') is not None}
    invalid=[i for i,r in enumerate(rows) if r['start']<0 or r['end']<r['start'] or r['end']>duration+0.1]
    return {'count':len(rows),'zero_duration':sum(d==0 for d in lengths),'negative_duration':sum(d<0 for d in lengths),
        'median_duration_seconds':statistics.median(lengths) if lengths else None,
        'less_than_0_5s':sum(0<=d<0.5 for d in lengths),'less_than_1s':sum(0<=d<1 for d in lengths),
        'less_than_2s':sum(0<=d<2 for d in lengths),
        'empty_text':sum(not r.get('text','').strip() for r in rows) if has_text else None,
        'invalid_time_indices':invalid,'speaker_groups':len(groups) if groups else None,
        'unassigned_segment_count':sum(r.get('speaker') is None for r in rows) if any('speaker' in r for r in rows) else None,
        'speaker_group_count_is_accuracy':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('folder');args=parser.parse_args()
    folder=ROOT/args.folder
    if (folder/'asr-request.json').is_file():
        request=read(folder/'asr-request.json');asr=read(folder/'asr-result.json')['result'];diar=read(folder/'sherpa-result.json')['result']
    else:
        request=read(folder/'request.json');output=read(folder/'result.json')['result']
        import wave
        with wave.open(request['audio'],'rb') as f:duration=f.getnframes()/f.getframerate()
        raw=output.get('segments',output.get('turns',[]))
        stats={'engine_task':request['task'],'segments':describe(raw,duration,has_text='segments' in output),
            'WER':None,'DER':None,'cpWER':None,'cpCER':None,
            'score_status':'Qualitative reference only; exhaustive scoring annotations unavailable.',
            'confidence_status':'Not a calibrated confidence' if request['task']=='moss' else 'See engine-specific raw confidence fields'}
        write(folder/'statistics.json',stats)
        normalized=[{**r,'id':f"{request['task']}-{i}"} for i,r in enumerate(raw)]
        write(folder/'transcript.json',{'segments':normalized,'names_assigned':False,'original_case_audio':request['audio']})
        lines=['# Sortie expérimentale '+request['task'],'','Horodatages relatifs au clip. Identifiants propres à cet essai, sans identité nominative reconnue.','']
        lines += [f"- {r['start']:.3f}–{r['end']:.3f} s · {r.get('speaker') or 'non attribué'} : {r.get('text','')}" for r in raw]
        write(folder/'transcript.md','\n'.join(lines));print(stats);return
    import wave
    with wave.open(request['audio'],'rb') as f:duration=f.getnframes()/f.getframerate()
    rows,speakers=align_reference(asr['segments'],diar)
    normalized=[{'start':r['start_ms']/1000,'end':r['end_ms']/1000,'speaker':r['speaker_id'],'text':r['text'],
                 'uncertain':r['uncertain'],'source':r['source'],'id':r['id']} for r in rows]
    write(folder/'transcript.json',{'segments':normalized,'speaker_aliases':speakers,
        'names_assigned':False,'original_case_audio':request['audio']})
    stats={'asr':describe(asr['segments'],duration,has_text=True),'diarization':describe(diar['turns'],duration),
        'combined':describe(normalized,duration,has_text=True),'uncertain_combined_count':sum(r['uncertain'] for r in normalized),
        'possible_overlaps':diar.get('possible_overlaps',[]),'WER':None,'DER':None,'cpWER':None,'cpCER':None,
        'score_status':'No exhaustive human verbatim / speaker-interval annotation; qualitative reference only.'}
    write(folder/'statistics.json',stats)
    lines=['# Transcription expérimentale A — non corrigée','',
           'Identifiants anonymes propres à cet essai. Aucun nom reconnu ou attribué automatiquement.','']
    lines += [f"- {r['start']:.3f}–{r['end']:.3f} s · {r['speaker'] or 'inconnu'} · {'À vérifier' if r['uncertain'] else 'aucun signal automatique'} : {r['text']}" for r in normalized]
    write(folder/'transcript.md','\n'.join(lines))
    print(stats)


if __name__=='__main__':main()
