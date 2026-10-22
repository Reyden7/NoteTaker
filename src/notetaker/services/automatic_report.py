"""Orchestrate existing audio engines, optional voice matching and direct Qwen."""
import json
import time
from pathlib import Path
from notetaker.infrastructure.atomic import sha256_file, atomic_json
from notetaker.infrastructure.paths import session_directory
from notetaker.infrastructure.process import JobCancelled
from .storage import SessionStore
from .audio import prepare_audio


def speaker_labels(state):
    from notetaker.domain.summary import voice_registry
    registry=voice_registry(state)
    result = {}
    for index, (sid, label) in enumerate(state['speakers'].items(),1):
        records = [u for u in state['utterances'] if u.get('speaker_id')==sid]
        confirmed = registry.get(sid,{}).get('confirmed',False)
        result[sid] = label if confirmed else f'Intervenant non identifié (voix {index})'
    return result


def generate(pipeline, sid):
    store = SessionStore(pipeline.root)
    started = time.perf_counter()
    jid = store.start_job(sid, 'automatic-report')
    workspace = session_directory(pipeline.root,sid)/'jobs'/jid
    workspace.mkdir(parents=True)
    try:
        state = store.get(sid)
        takes = [t for t in state['takes'] if t.get('enabled',1)]
        if state['takes'] and not takes:
            raise ValueError('Aucune prise sélectionnée. Sélectionnez un enregistrement dans le mode avancé avant de générer.')
        reuse = bool(state['utterances'])
        if reuse:
            paths = {json.loads(u['source_json']).get('normalized_audio') for u in state['utterances']}
            if None in paths or not all(Path(p).is_file() for p in paths):
                raise ValueError('L’audio lié à la transcription est absent. Restaurez sa copie avant de générer le compte rendu.')
            digests = {sha256_file(Path(p)) for p in paths}
            if takes:
                pipeline.progress('Vérification du montage audio — la transcription existante sera réutilisée si les sources sont identiques')
                selected = prepare_audio(takes,workspace/'selected-audio.wav',pipeline.progress)
                reuse = digests == {sha256_file(selected)}
            else:
                reuse = len(digests)==1
        if pipeline.cancel.is_set(): raise JobCancelled('JOB_CANCELLED')
        if not reuse:
            pipeline.progress('Transcription et diarisation avec le moteur audio configuré')
            pipeline.analyse(sid)
            state = store.get(sid)
        if not state['utterances']: raise ValueError('Aucune transcription exploitable. Importez ou enregistrez une réunion.')
        pipeline.progress('Correspondance vocale facultative — aucune identité n’est devinée')
        from .voice_profiles import identify_session
        recognition = identify_session(store,state,pipeline.models,pipeline.cancel)
        state = store.get(sid)
        context = store.context_hash(sid)
        labels = speaker_labels(state)
        from notetaker.domain.summary import voice_registry
        voices=voice_registry(state)
        templates={key:('{{V1}}' if labels.get(key)==state['speakers'].get(key) else
            'Intervenant non identifié ({{V1}})') for key in voices}
        for key, value in recognition.get('labels',{}).items():
            if key in templates and not voices[key]['confirmed']:
                templates[key]='{{V1}} (identité vocale proposée, à confirmer : '+value.replace('{','').replace('}','')+')'
        pipeline.models.verify()
        from notetaker.domain.minutes import content_digest
        cache_key=content_digest({'session_id':sid,'context':context,'labels':labels,'templates':templates,
            'engine':{name:sha256_file(Path(__file__).parents[1]/'engines'/name) for name in
                ('automatic_report.py','editorial_report.py','topic_summary.py','hierarchical_summary.py')},
            'model':str(pipeline.models.llm),'mtime':pipeline.models.llm.stat().st_mtime_ns if pipeline.models.llm.is_file() else None})
        # Keep native llama prompt paths below Windows MAX_PATH, even when the
        # session UUID and recipe workspace already make a deep directory tree.
        cache=pipeline.root/'automatic-cache'/cache_key[:24]
        if len(str(cache/'automatic-check-0000.prompt.txt'))>=250:
            raise ValueError('Le dossier de données est trop long pour le moteur Windows. Utilisez un chemin de recette plus court ; les sources restent conservées.')
        cache.mkdir(parents=True,exist_ok=True)
        marker=cache/'cache-key.json'
        if marker.exists() and json.loads(marker.read_text(encoding='utf-8'))!={'sha256':cache_key}:
            raise ValueError('Collision de cache détectée. Les résultats antérieurs sont conservés ; choisissez un dossier de recette distinct.')
        atomic_json(marker,{'sha256':cache_key})
        # Resume exact, individually validated call_json identities from prior jobs.
        # The helper rechecks prompt/schema/model/binary before accepting any result.
        import shutil
        previous_requests=sorted((session_directory(pipeline.root,sid)/'jobs').glob('*/llm-cpu.request.json'),
            key=lambda p:p.stat().st_mtime_ns,reverse=True)
        for prior in previous_requests:
            try: old=json.loads(prior.read_text(encoding='utf-8'))
            except (ValueError,OSError):continue
            if old.get('task')!='automatic_report' or any(old.get(k)!=v for k,v in {
                'utterances':state['utterances'],'agenda':state['metadata'].get('agenda',[]),
                'lexicon':state['metadata'].get('lexicon',[])}.items()):continue
            folders=[prior.parent]
            if old.get('cache_workspace'):
                prior_cache=Path(old['cache_workspace']).resolve()
                if prior_cache.is_relative_to(pipeline.root.resolve()):folders.append(prior_cache)
            for folder in folders:
                for item in list(folder.glob('automatic-*.json'))+list(folder.glob('editorial-*.json')):
                    if item.name.endswith(('.identity.json','.result.json')) and not (cache/item.name).exists():
                        shutil.copyfile(item,cache/item.name)
        preexisting_cache_results=sorted(p.name for p in cache.glob('*.result.json'))
        pipeline.progress('Qwen prépare le brouillon directement depuis la transcription — aucune fiche à préapprouver')
        request = {'engine':'llm','task':'automatic_report','editorial_v4':True,'discourse_anchors':True,'device':'cpu','binary':str(pipeline.models.llama),
            'repair_rejected':True,'sentence_evidence':True,
            'model':str(pipeline.models.llm),'workspace':str(workspace),'cache_workspace':str(cache),'utterances':state['utterances'],
            'agenda':state['metadata'].get('agenda',[]),'lexicon':state['metadata'].get('lexicon',[]),
            'summary_length':state['metadata'].get('summary_length','standard'),
            'speaker_labels':{k:v['label'] for k,v in voices.items()},'speaker_templates':templates}
        result = pipeline._run(workspace, request, timeout=14400)
        draft = result.get('result',result)
        if recognition.get('warning'): draft['to_verify'].append(recognition['warning'])
        if pipeline.cancel.is_set(): raise JobCancelled('JOB_CANCELLED')
        store.save_draft(sid,draft,expected_context=context,allow_invalid=True)
        report = {'points':len(draft['points']),'transcription_reused':reuse,
            'paraphrase_claims':draft.get('generation_diagnostics',{}).get('paraphrase_claims',0),
            'quoted_fallback_points':draft.get('generation_diagnostics',{}).get('quoted_fallback_points',0),
            'cache_results_available_before_run':preexisting_cache_results,
            'voice_recognition':recognition,'elapsed_seconds':round(time.perf_counter()-started,3),
            'review_created':False,'workspace':str(workspace)}
        atomic_json(workspace/'automatic-report.json',report)
        store.finish_job(jid,True)
        return report
    except BaseException as error:
        store.finish_job(jid,False,'CANCELLED' if isinstance(error,JobCancelled) else type(error).__name__)
        raise
    finally:
        store.close()
