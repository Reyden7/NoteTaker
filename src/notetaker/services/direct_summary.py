"""Test-only orchestration, immutable provenance, and the unchanged export gates."""
import json
import uuid
from pathlib import Path
from notetaker.domain.direct_summary import VERSION, fingerprint, input_snapshot, test_workspace
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.paths import ModelPaths
from notetaker.infrastructure.process import run_worker
from notetaker.services.storage import SessionStore
from notetaker.services.pipeline import assemble_summary


def artifact_path(root, sid, run_id):
    if str(uuid.UUID(sid)) != sid or str(uuid.UUID(run_id)) != run_id:
        raise ValueError('DIRECT_PROVENANCE_INVALID')
    root = Path(root).resolve()
    path = root / 'sessions' / sid / 'direct-experiments' / run_id / 'result.json'
    if not path.resolve().is_relative_to(root):
        raise ValueError('DIRECT_PROVENANCE_INVALID')
    return path


def validate_provenance(store, sid, content):
    proof = content.get('experimental_summary')
    if not proof:
        return
    try:
        marker = test_workspace(store.root)
        path = artifact_path(store.root, sid, proof['run_id'])
        if proof['workspace_id'] != marker['id'] or sha256_file(path) != proof['artifact_sha256']:
            raise ValueError()
        result = json.loads(path.read_text(encoding='utf-8'))
        expected = fingerprint(store.get(sid))
        if proof['input_sha256'] != expected or result['input_sha256'] != expected:
            raise ValueError('DIRECT_SOURCES_CHANGED')
        if result['run_id'] != proof['run_id'] or result['session_id'] != sid or result['version'] != VERSION:
            raise ValueError()
    except ValueError as error:
        if str(error) == 'DIRECT_SOURCES_CHANGED':
            raise
        raise ValueError('DIRECT_PROVENANCE_INVALID') from None
    except (OSError, KeyError, TypeError):
        raise ValueError('DIRECT_PROVENANCE_INVALID') from None


class DirectSummaryService:
    def __init__(self, root, *, enabled=False, models=None, progress=lambda _: None, cancel=None):
        if not enabled:
            raise ValueError('DIRECT_TEST_COPY_REQUIRED')
        self.root = Path(root).resolve()
        self.marker = test_workspace(self.root)
        self.models = models or ModelPaths()
        self.progress, self.cancel = progress, cancel

    def generate(self, sid, *, summary_length='standard', resume_id=None):
        store = SessionStore(self.root)
        run_id = resume_id or str(uuid.uuid4())
        artifact = artifact_path(self.root, sid, run_id)
        workspace = artifact.parent / 'inference'
        try:
            state = store.get(sid)
            context = store.context_hash(sid)
            source_sha = fingerprint(state)
            if summary_length not in ('short', 'standard', 'detailed'):
                raise ValueError('DIRECT_INVALID_LENGTH')
            if artifact.exists():
                raise ValueError('DIRECT_COMPLETED_RUN_IMMUTABLE')
            workspace.mkdir(parents=True, exist_ok=bool(resume_id))
            request = {'engine': 'llm', 'task': 'direct_summary', 'experimental_direct': True,
                'pipeline_version': VERSION,
                'test_root': str(self.root), 'workspace': str(workspace), 'cache_mode': 'resume' if resume_id else 'cold',
                'binary': str(self.models.llama), 'model': str(self.models.llm), 'device': 'cpu',
                'summary_length': summary_length, 'run_id': run_id, **input_snapshot(state)}
            request_path = artifact.parent / 'request.json'
            if resume_id:
                previous = json.loads(request_path.read_text(encoding='utf-8'))
                if previous.get('pipeline_version') != VERSION:
                    raise ValueError('DIRECT_EXPERIMENT_VERSION_CHANGED')
                if any(previous.get(k) != request.get(k) for k in ('utterances', 'speakers', 'agenda', 'lexicon', 'summary_length')):
                    raise ValueError('DIRECT_SOURCES_CHANGED')
            self.models.verify()
            atomic_json(request_path, request)
            self.progress('Essai direct CPU : contextes longs, regroupement, puis contrôles ciblés. Aucune relecture créée.')
            response = self.run(request_path)
            atomic_json(artifact.parent/'response.json', response)
            result = response['result']
            mode = 'municipal' if state['metadata'].get('document_mode') == 'municipal' else 'summary'
            draft = assemble_summary(state, result, mode=mode)
            record = {'version': VERSION, 'run_id': run_id, 'session_id': sid, 'input_sha256': source_sha,
                'input': input_snapshot(state), 'result': result, 'workspace_id': self.marker['id'],
                'profile': json.loads((workspace/'direct-profile.json').read_text(encoding='utf-8'))
                           if (workspace/'direct-profile.json').exists() else None,
                'human_review_created': False, 'quality_validated': False}
            atomic_json(artifact, record)
            if not draft['points']:
                return {'run_id': run_id, 'draft_saved': False, 'reason': 'Aucun paragraphe admissible ; consulter les rejets et sources.'}
            draft['experimental_summary'] = {'run_id': run_id, 'workspace_id': self.marker['id'],
                'artifact_sha256': sha256_file(artifact), 'input_sha256': source_sha}
            draft['to_verify'].insert(0, 'ESSAI EXPÉRIMENTAL — qualité non validée. Consulter les alertes et l’inventaire des omissions puis relire intégralement.')
            did = store.save_draft(sid, draft, expected_context=context)
            return {'run_id': run_id, 'draft_id': did, 'draft_saved': True,
                    'paragraphs': len(draft['points']), 'alerts': len(result['ledger']['alerts'])}
        finally:
            store.close()

    def run(self, request_path):
        return run_worker(request_path, timeout=14400, cancel=self.cancel)

    def reuse(self, sid, run_id):
        """Explicitly restore completed prose as a NEW unreviewed revision, no AI."""
        store = SessionStore(self.root)
        try:
            state = store.get(sid)
            context = store.context_hash(sid)
            path = artifact_path(self.root, sid, run_id)
            record = json.loads(path.read_text(encoding='utf-8'))
            # Anchor to a previously persisted receipt. Re-hashing an altered
            # file must not silently bless it as a new trusted result.
            proof = None
            for row in store.db.execute('SELECT content_json FROM draft_minutes WHERE session_id=? ORDER BY revision', (sid,)):
                previous = json.loads(row[0]).get('experimental_summary')
                if previous and previous.get('run_id') == run_id:
                    proof = previous
                    break
            if proof is None:
                raise ValueError('DIRECT_PROVENANCE_INVALID')
            validate_provenance(store, sid, {'experimental_summary': proof})
            mode = 'municipal' if state['metadata'].get('document_mode') == 'municipal' else 'summary'
            draft = assemble_summary(state, record['result'], mode=mode)
            if not draft['points']:
                raise ValueError('NO_SUPPORTED_TOPIC_PARAGRAPHS')
            draft['experimental_summary'] = proof
            draft['to_verify'].insert(0, 'Résultat expérimental réutilisé sans nouvelle inférence. Nouvelle révision à relire intégralement ; qualité non validée.')
            did = store.save_draft(sid, draft, expected_context=context)
            return {'draft_id': did, 'run_id': run_id, 'fresh_calls': 0, 'human_review_created': False}
        finally:
            store.close()


def experiments(root, sid):
    directory = Path(root)/'sessions'/sid/'direct-experiments'
    results = []
    for path in directory.glob('*/result.json'):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            results.append((path.stat().st_mtime_ns, data))
        except (OSError, ValueError):
            continue
    return [data for _, data in sorted(results, key=lambda row: row[0], reverse=True)]
