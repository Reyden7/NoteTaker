"""Revised isolated protocol, same prompt and native parameters for A/B/C.

Consecutive equal-author fragments are concatenated without selecting information.
Short turn IDs replace repetitive fragment lists in the MODEL interface only;
the full turn -> original segment -> time map remains in each archived input.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from experiments.parcoursup_20261020.run_case import INSTRUCTION, DirectRuntime, NETWORK, atomic_json, literal_audit, render, schema
from experiments.parcoursup_20261020.prepare import OUT, ARTIFACT, read, sha
from experiments.parcoursup_20261020.import_human import V2

COMPACT_INSTRUCTION = INSTRUCTION + (
    ' Les passages sont des tours de parole : leur identifiant Txxx renvoie au catalogue complet de segments et horodatages archivé séparément. '
    'Utilise ces identifiants courts Txxx dans sources et source_id. Écris un JSON COMPACT, sans indentation. '
    'Les réponses restent concises : une phrase par argument ou proposition distincte, sans dupliquer la même information entre rubriques. '
    'Les références sont les tours strictement utiles ; ne recopie pas des listes de segments ni des tours entiers. '
    'Une citation courte et littérale (environ 5 à 15 mots) par tour cité suffit ; ne la duplique pas. '
    'Aucun nombre attendu de participants ou de propositions n’est imposé.'
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case',required=True,choices=['A-original','B-corrigee-humaine','C-corrigee-contexte'])
    args = parser.parse_args()
    protected = read(OUT/'manifest.json')['protected_files']
    path = V2/'inputs'/(args.case+'.json')
    receipt = read(V2/'provenance-humaine.json')
    if receipt['cases'][args.case]['sha256'] != sha(path): raise ValueError('INPUT_CHANGED_SINCE_HUMAN_IMPORT')
    if sha(V2/'correction-humaine-originale.txt') != receipt['human_file_sha256']: raise ValueError('HUMAN_COPY_CHANGED')
    if not all(sha(p)==h for p,h in protected.items()): raise ValueError('PROTECTED_SOURCE_CHANGED')
    work = V2/'runs'/args.case; work.mkdir(parents=True,exist_ok=False)
    old = read(ARTIFACT.parent/'request.json')
    request = {k:old[k] for k in ('binary','model')}; request.update(workspace=str(work),cache_mode='cold')
    inputs = read(path)
    payload = {k:inputs[k] for k in ('focus_start_ms','focus_end_ms','context_status')}
    payload['passages'] = [{k:r[k] for k in ('id','start_ms','end_ms','speaker_label','text')} for r in inputs['turns']]
    started = time.perf_counter()
    report = {'protocol':'compact-turns-v2','status':'running','case':args.case,
        'started_at_utc':datetime.now(timezone.utc).isoformat(),'input_sha256':sha(path),
        'human_reference_given_to_qwen':False,'production_pipeline_called':False,
        'quality_validated':False,'human_corrected_scope':'none' if args.case=='A-original' else 'focal_only',
        'context_extension_human_corrected':False}
    atomic_json(work/'report.json',report)
    (work/'instruction.txt').write_text(COMPACT_INSTRUCTION,encoding='utf-8')
    runtime = None
    try:
        runtime = DirectRuntime(request)
        result = runtime.call('isolated-000',COMPACT_INSTRUCTION,payload,schema(),tokens=3000)
        audit = literal_audit(result,{**inputs,'passages':inputs['turns']})
        atomic_json(work/'literal-audit.json',audit)
        (work/'synthese.md').write_text(render(result,args.case),encoding='utf-8')
        report.update(status='completed',counts={k:len(v) for k,v in result.items() if isinstance(v,list)},
                      literal_issue_count=len(audit['issues']))
    except BaseException as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error))
        raise
    finally:
        report.update(wall_seconds_including_model_hashes=time.perf_counter()-started,
            protected_sources_unchanged=all(sha(p)==h for p,h in protected.items()),
            python_network_attempts=len(NETWORK),profile=runtime.profile if runtime else [])
        atomic_json(work/'report.json',report)
        print(json.dumps({k:v for k,v in report.items() if k!='profile'},ensure_ascii=True),flush=True)


if __name__ == '__main__': main()
