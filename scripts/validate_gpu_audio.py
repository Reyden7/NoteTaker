"""Production audio integration on a NEW isolated session; no quality approval.

The separate export fixture exercises existing gates, never approves the
municipal session or claims that its transcript/PV was reviewed by a person.
"""
import argparse
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.paths import session_directory
from notetaker.services.audio import import_audio
from notetaker.services.pipeline import Pipeline
from notetaker.services.storage import SessionStore
from notetaker.services.session_export import export_session


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--mode', choices=['auto', 'gpu', 'cpu'], default='gpu')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    root = args.output / 'application-data'
    store = SessionStore(root)
    report = {'quality_human_validated': False, 'cold_run': False, 'mode': args.mode,
              'source_sha256': sha256_file(args.audio)}
    try:
        sid = store.create('Essai intégration audio GPU — municipal — À RELIRE')
        copied, digest = import_audio(args.audio, session_directory(root, sid))
        store.add_take(sid, 'import', copied, sha256=digest)
        report['session_id'] = sid
        started = time.perf_counter()
        pipeline = Pipeline(root, progress=lambda msg: print(msg, flush=True))
        report['analysis'] = pipeline.analyse(sid, args.mode)
        report['elapsed_import_to_analysis_seconds'] = time.perf_counter() - started
        report['draft'] = pipeline.generate(sid, 'transcript')
        for suffix in ['pdf', 'docx']:
            try:
                export_session(store, sid, args.output / ('unreviewed.' + suffix))
            except ValueError as error:
                report['unreviewed_' + suffix + '_blocked'] = 'HUMAN_REVIEW' in str(error)
                assert report['unreviewed_' + suffix + '_blocked']
            else:
                raise AssertionError('UNREVIEWED_EXPORT_ACCEPTED')
        state = store.get(sid)
        report['overlapping_rows'] = sum(bool(json.loads(u['source_json']).get('simultaneous_turns')) for u in state['utterances'])
        report['votes_not_inferred'] = not state['votes'] and not state['decisions']
        report['input_intact'] = digest == sha256_file(args.audio) == sha256_file(copied)
    finally:
        store.close()
    reopened = SessionStore(root)
    try:
        state = reopened.get(sid)
        report['reopened'] = len(state['utterances']) == report['analysis']['utterances'] and state['draft']['review'] is None
        # Separate fixture DB, explicitly artificial review, no municipal session approval.
        fixture = SessionStore(args.output / 'export-fixture')
        try:
            fid = fixture.create('TEST AUTOMATISÉ DES EXPORTS — PAS UNE RELECTURE HUMAINE')
            rows = [{k: u[k] for k in ['id', 'start_ms', 'end_ms', 'text', 'speaker_id', 'uncertain']} |
                    {'source': json.loads(u['source_json'])} for u in state['utterances']]
            fixture.save_analysis(fid, rows, state['speakers'], 0)
            Pipeline(fixture.root).generate(fid, 'transcript')
            fixture.approve(fid, 'TEST AUTOMATISÉ UNIQUEMENT — AUCUNE VALIDATION DU CONSEIL')
            for suffix in ['pdf', 'docx']:
                export_session(fixture, fid, args.output / ('export-test-only.' + suffix))
            report['fixture_exports'] = ['pdf', 'docx']
        finally:
            fixture.close()
    finally:
        reopened.close()
    atomic_json(args.output / 'report.json', report)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
