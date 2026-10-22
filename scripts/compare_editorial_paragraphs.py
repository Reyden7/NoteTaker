"""Structural comparison and preservation checks; never a semantic score."""
import argparse
import json
import sqlite3
from pathlib import Path
from notetaker.infrastructure.atomic import atomic_json,sha256_file
from notetaker.services.storage import SessionStore
from notetaker.services.evidence import draft_issues


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline-root',type=Path,required=True)
    parser.add_argument('--current-root',type=Path,required=True)
    parser.add_argument('--session-id',required=True)
    parser.add_argument('--delivery',default='livrables')
    parser.add_argument('--comparison-dir',type=Path)
    args=parser.parse_args()
    old=read(args.baseline_root/'livrables-v4/result.json')
    new=read(args.current_root/args.delivery/'result.json')
    original=Path(old['workspace']).parents[3]/'notetaker.sqlite3'
    current=args.current_root/'data/notetaker.sqlite3'
    preservation={}
    with sqlite3.connect(original.resolve().as_uri()+'?mode=ro',uri=True) as a:
        with sqlite3.connect(current.resolve().as_uri()+'?mode=ro',uri=True) as b:
            for table, in a.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                if table.startswith('sqlite_') or table in ('job','draft_minutes'):continue
                query='SELECT * FROM "'+table+'"'
                preservation[table]=sorted(a.execute(query).fetchall(),key=repr)==sorted(b.execute(query).fetchall(),key=repr)
            before=a.execute('SELECT * FROM draft_minutes').fetchall()
            after=b.execute('SELECT * FROM draft_minutes').fetchall()
            preservation['all_previous_drafts']=all(row in after for row in before)
            preservation['new_drafts_without_review']=all(row[4] is None for row in after if row not in before)
    assert all(preservation.values()),preservation
    store=SessionStore(current.parent);state=store.get(args.session_id)
    issues=draft_issues(new['content'],state);store.close()
    assert not issues,issues
    sources={r['id']:r for r in state['utterances']}
    audio_sources={path:sha256_file(Path(path)) for path in {
        json.loads(r['source_json'])['normalized_audio'] for r in sources.values()}}
    old_points=old['content']['points'];new_points=new['content']['points']
    old_entries=[];new_entries=[]
    for i,p in enumerate(old_points,1):
        matches=[j for j,q in enumerate(new_points,1) if set(p['sources'])&set(q['sources'])]
        old_entries.append({'paragraph':i,'title':p['title'],'text':p['summary'],'sources':p['sources'],
                            'new_paragraphs_sharing_sources':matches})
    for i,p in enumerate(new_points,1):
        entries=[]
        for claim in p.get('claims',[]):
            for evidence in claim['evidence']:
                source=sources[evidence['id']]
                assert evidence['quote'] in source['text'] and source['end_ms']>source['start_ms']
                assert (source.get('speaker_id') or 'unattributed')==claim['speaker']
            entries.append({'text':claim['text'],'author':claim['speaker'],
                'evidence':[{'id':e['id'],'quote':e['quote'],'start_ms':sources[e['id']]['start_ms'],
                    'end_ms':sources[e['id']]['end_ms'],
                    'audio':json.loads(sources[e['id']]['source_json'])['normalized_audio']} for e in claim['evidence']]})
        new_entries.append({'paragraph':i,'title':p['title'],'text':p['summary'],'sentences':entries,
            'old_paragraphs_sharing_sources':[e['paragraph'] for e in old_entries if i in e['new_paragraphs_sharing_sources']]})
    cache=Path(read(Path(new['workspace'])/'llm-cpu.request.json')['cache_workspace'])
    timings={p.name:read(p) for p in cache.glob('*.timing.json')}
    comparison={'old_paragraphs':old_entries,'new_paragraphs':new_entries,
        'matching_is_structural_not_semantic':True,'source_audio_listened_by_agent':False,
        'audio_sources_sha256':audio_sources,
        'human_fidelity_measured':False,'preservation':preservation,'draft_issues':issues,
        'elapsed_seconds':new['elapsed_seconds'],'new_native_calls':timings,'delivery':args.delivery,
        'engine_sources_sha256':{str(p):sha256_file(p) for p in [Path('src/notetaker/engines/editorial_report.py'),
            Path('src/notetaker/domain/summary.py'),Path('src/notetaker/schemas/minutes.json')]}}
    destination=args.comparison_dir or args.current_root
    destination.mkdir(parents=True,exist_ok=True)
    atomic_json(destination/'comparaison-paragraphes.json',comparison)
    lines=['# Comparaison exhaustive des paragraphes','',
        'Rapprochement structurel par sources communes, pas un score de fidélité. Les commentaires de sens sont dans le rapport d’audit.',
        'Vérification de l’agent contre la transcription conservée ; pas de nouvelle écoute ou de validation humaine de l’audio.','']
    for path in audio_sources:
        lines+=['[Enregistrement de référence — horaires ci-dessous relatifs à ce fichier]('+Path(path).as_posix()+')','']
    for entry in old_entries:
        lines+=['## Ancien paragraphe '+str(entry['paragraph'])+' — '+entry['title'],'',entry['text'],'',
            'Sources : '+', '.join(entry['sources']),'']
        for index in entry['new_paragraphs_sharing_sources']:
            p=new_entries[index-1]
            lines+=['### Nouveau paragraphe '+str(index)+' — '+p['title'],'',p['text'],'']
        if not entry['new_paragraphs_sharing_sources']:lines+=['Aucune phrase retenue ne partage ces sources ; omission à examiner.','']
    for entry in new_entries:
        if not entry['old_paragraphs_sharing_sources']:
            lines+=['## Nouveau paragraphe supplémentaire '+str(entry['paragraph']),'',entry['title'],'',entry['text'],'']
    lines+=['## Chaque phrase et ses sources exactes','']
    for entry in new_entries:
        lines+=['### Paragraphe '+str(entry['paragraph']),'']
        for sentence in entry['sentences']:
            lines += [sentence['text'],'']
            for e in sentence['evidence']:
                lines += [f"{e['id']} — {e['start_ms']/1000:.3f} à {e['end_ms']/1000:.3f} s",'',e['quote'],'']
    (destination/'comparaison-paragraphes.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'preservation':preservation,'old_paragraphs':len(old_entries),
        'new_paragraphs':len(new_entries),'new_native_calls':len(timings)},ensure_ascii=False))


if __name__=='__main__':main()
