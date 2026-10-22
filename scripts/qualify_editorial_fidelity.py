"""Real municipal recipe on an isolated SQLite backup; no audio inference.

Individual old Qwen results are seeded with their original cache identities.
call_json must still verify the exact prompt, schema, model and binary.
"""
import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from notetaker.infrastructure.atomic import atomic_json
from notetaker.infrastructure.offline import enforce_offline
from notetaker.services.storage import SessionStore
from notetaker.services.pipeline import Pipeline
from notetaker.services.working_export import export_working_copy
from notetaker.services.session_export import export_session


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--session-id',required=True)
    args=parser.parse_args();enforce_offline()
    args.output.mkdir(parents=True,exist_ok=False)
    old_result=args.baseline_root/'livrables-v4/result.json'
    old=json.loads(old_result.read_text(encoding='utf-8'))
    old_job=Path(old['workspace']);old_root=old_job.parents[3]
    original=old_root/'notetaker.sqlite3'
    request=json.loads((old_job/'llm-cpu.request.json').read_text(encoding='utf-8'))
    protected=[original,old_result,*[args.baseline_root/'livrables-v4'/('Compte-rendu-BROUILLON.'+s) for s in ('pdf','docx')]]
    protected+=[Path(json.loads(u['source_json'])['normalized_audio']) for u in request['utterances']]
    hashes={str(p):digest(p) for p in dict.fromkeys(protected)}
    root=args.output/'data';root.mkdir()
    with sqlite3.connect(original.resolve().as_uri()+'?mode=ro',uri=True) as src:
        with sqlite3.connect(root/'notetaker.sqlite3') as dst:src.backup(dst)
    seed=root/'sessions'/args.session_id/'jobs'/'seed-original-cache'
    seed.mkdir(parents=True)
    for folder in (old_job,Path(request['cache_workspace'])):
        for path in folder.glob('editorial-*.json'):
            if path.name.endswith(('.identity.json','.result.json')):shutil.copyfile(path,seed/path.name)
    request['cache_workspace']=str(seed)
    atomic_json(seed/'llm-cpu.request.json',request)
    atomic_json(args.output/'cache-provenance.json',{'original_job':str(old_job),
        'seeded_identity_and_result_files':sorted(p.name for p in seed.glob('editorial-*.json')),
        'timing_files_copied':False})
    store=SessionStore(root);state=store.get(args.session_id)
    before={k:state[k] for k in ('utterances','speakers','votes','decisions','participants')}
    result=Pipeline(root,progress=lambda s:print(s,flush=True)).automatic_report(args.session_id)
    after=store.get(args.session_id)
    assert all(after[k]==v for k,v in before.items())
    assert after['draft']['review'] is None and result['transcription_reused']
    delivery=args.output/'livrables';delivery.mkdir()
    for suffix in ('pdf','docx'):
        export_working_copy(store,args.session_id,delivery/('Compte-rendu-BROUILLON.'+suffix))
    try:export_session(store,args.session_id,delivery/'OFFICIEL-INTERDIT.pdf')
    except ValueError:blocked=True
    else:blocked=False
    assert blocked and all(digest(Path(p))==value for p,value in hashes.items())
    result.update(content=after['draft']['content'],protected_files_unchanged=hashes,
        session_sources_unchanged=True,official_export_blocked=True,
        human_fidelity_measured=False,source_audio_listened_by_agent=False)
    atomic_json(delivery/'result.json',result)
    for name in ('verification-report.md','automatic-inventory.json','coverage-before-writing.json','editorial-plan.json'):
        shutil.copyfile(Path(result['workspace'])/name,args.output/name)
    store.close()
    print(json.dumps({k:v for k,v in result.items() if k not in ('content','protected_files_unchanged')},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
