"""Build an honest comparison and an unapproved local review session.

Optional human references allow pairwise clustering precision/recall and WER;
without them, accuracy, topic coverage and hallucination rate remain null.
"""
import argparse
import json
import re
import shutil
import sys
import uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.paths import session_directory
from notetaker.services.pipeline import assemble_summary, integral_transcript
from notetaker.services.storage import SessionStore
from notetaker.services.audio import import_audio
from notetaker.services.session_export import export_session
from notetaker.services.export import _pdf, _docx


def words(text):
    return re.findall(r"\w+(?:['’]\w+)*", text.casefold())


def word_error(reference, hypothesis):
    ref, hyp = words(reference), words(hypothesis)
    previous = list(range(len(hyp) + 1))
    for i, a in enumerate(ref, 1):
        row = [i]
        for j, b in enumerate(hyp, 1):
            row.append(min(row[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = row
    return {'reference_words': len(ref), 'errors': previous[-1], 'wer': previous[-1] / len(ref) if ref else None}


def reference_metrics(annotations, utterances):
    assigned, reference, hypothesis = [], [], []
    for sample in annotations.get('segments', []):
        matching = [u for u in utterances if u['start_ms'] < sample['end_ms'] and u['end_ms'] > sample['start_ms']]
        durations = {}
        for u in matching:
            overlap = max(0, min(u['end_ms'], sample['end_ms']) - max(u['start_ms'], sample['start_ms']))
            durations[u['speaker_id']] = durations.get(u['speaker_id'], 0) + overlap
        assigned.append((sample['speaker'], max(durations, key=durations.get) if durations else None))
        reference.append(sample['text'])
        hypothesis.append(' '.join(u['text'] for u in matching))
    tp = fp = fn = 0
    for i, (actual_a, predicted_a) in enumerate(assigned):
        for actual_b, predicted_b in assigned[i + 1:]:
            same_actual = actual_a == actual_b
            same_predicted = predicted_a is not None and predicted_a == predicted_b
            tp += same_actual and same_predicted
            fp += not same_actual and same_predicted
            fn += same_actual and not same_predicted
    return {'pairwise_precision': tp / (tp + fp) if tp + fp else None,
            'pairwise_recall': tp / (tp + fn) if tp + fn else None,
            'annotated_segments': len(assigned), 'pairwise_not_der': True,
            'wer': word_error(' '.join(reference), ' '.join(hypothesis))}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--reference', type=Path)
    p.add_argument('--original-audio', type=Path, required=True)
    p.add_argument('--result-directory', type=Path)
    p.add_argument('--destination', type=Path)
    p.add_argument('--report', type=Path, default=ROOT / 'docs/evidence/quality-02-comparison.json')
    args = p.parse_args()
    work = ROOT / 'output/quality-02'
    results = (args.result_directory or work).resolve()
    destination = (args.destination or work).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    baseline = json.loads((work / 'baseline/records.json').read_text(encoding='utf-8'))
    initial = json.loads((work / 'baseline/statistics.json').read_text(encoding='utf-8'))
    aligned = json.loads((work / 'aligned-transcript.json').read_text(encoding='utf-8'))
    result = json.loads((results / 'summary-result.json').read_text(encoding='utf-8'))['result']
    review_root = destination / 'review-session'
    if (review_root / 'notetaker.sqlite3').exists():
        raise SystemExit('Review session already exists; preserve it and use a fresh benchmark directory')
    store = SessionStore(review_root)
    sid = store.create('Débat télévisé — recette 0.2 non validée', {'date': '2026-10-16', 'notes': 'Comparaison sur la dérivation 0.1, prise micro de 9,899 s incluse avant le MP3.'})
    directory = session_directory(review_root, sid)
    for take in baseline['audio_take']:
        if not take['enabled']:
            continue
        if take['kind'] == 'import':
            path, digest = import_audio(Path(take['path']), directory)
            store.add_take(sid, 'import', path, sha256=digest)
        else:
            path = directory / 'captures' / str(uuid.uuid4())
            shutil.copytree(take['path'], path)
            store.add_take(sid, 'capture', path)
    request_file = results / 'summary-request.json'
    rows = json.loads(request_file.read_text(encoding='utf-8'))['utterances'] if request_file.exists() else aligned['utterances']
    for u in rows:
        u['source']['normalized_audio'] = str(work / 'input-normalized.wav')
    store.save_analysis(sid, rows, aligned['speakers'], store.get(sid)['revision'])
    state = store.get(sid)
    draft = assemble_summary(state, result)
    store.save_draft(sid, draft)
    try:
        export_session(store, sid, destination / 'must-not-export.pdf')
    except ValueError as error:
        if 'HUMAN_REVIEW' not in str(error):
            raise
        review_error = str(error)
        blocked = True
    else:
        raise AssertionError('Real meeting was exported without review')
    details = {'title': 'Débat télévisé français — essai comparatif', 'preview': True}
    # Technical previews clearly marked as unapproved, without creating a review or export record.
    _pdf(draft, 'Recette locale 0.2 | 16 octobre 2026', destination / 'summary-preview.pdf', [], [], details)
    _docx(draft, 'Recette locale 0.2 | 16 octobre 2026', destination / 'summary-preview.docx', [], [], details)
    from pypdf import PdfReader
    actual_pdf = PdfReader(destination / 'summary-preview.pdf')
    extracted = '\n'.join(page.extract_text() for page in actual_pdf.pages)
    report = {'status': 'comparative_test_not_human_acceptance', 'quality_acceptance': False,
        'baseline': {k: initial[k] for k in ('speakers', 'utterances', 'uncertain_utterances', 'draft_characters', 'verification_alerts', 'pdfs')},
        'corrected': {'speakers': len(aligned['speakers']), 'utterances': len(rows), 'uncertain_utterances': sum(bool(u['uncertain']) for u in rows),
                      'replacement_characters': sum(u['text'].count('\ufffd') for u in rows),
                      'summary_characters': sum(len(p['summary']) for p in draft['points']), 'topics': len(draft['points']),
                      'pdf_preview_pages': len(actual_pdf.pages), 'pdf_replacement_characters': extracted.count('\ufffd'),
                      'claims': result['diagnostics'], 'verification_alerts': len(draft['to_verify'])},
        'original_mp3_sha256': initial['original']['sha256'],
        'original_mp3_unchanged': sha256_file(args.original_audio) == initial['original']['sha256'],
        'original_import_unchanged': all(sha256_file(Path(t['path'])) == t['sha256'] for t in baseline['audio_take'] if t['kind'] == 'import'),
        'unreviewed_export_blocked': blocked, 'review_created': False,
        'review_session_directory': str(review_root), 'review_session_id': sid,
        'human_reference': 'not-available', 'human_metrics': None, 'topic_coverage': None, 'hallucination_rate': None}
    report['source_file_sha256'] = {str(p.relative_to(ROOT)): sha256_file(p) for p in [
        ROOT / 'src/notetaker/engines/hierarchical_summary.py', ROOT / 'src/notetaker/engines/speaker_refinement.py',
        ROOT / 'src/notetaker/workers/probe.py', ROOT / 'src/notetaker/services/pipeline.py', ROOT / 'src/notetaker/services/export.py']}
    selected = [c for point in draft['points'] for c in point.get('claims', [])]
    by_id = {u['id']: u for u in rows}
    source_ids = {e['id'] for c in selected for e in c['evidence']}
    report['corrected']['selected_claims'] = len(selected)
    report['corrected']['unselected_claims'] = len(result['claims']) - len(selected)
    from notetaker.engines.hierarchical_summary import grounded_claim
    report['automatic_source_check'] = {'selected_claims': len(selected),
        'claims_without_exact_citations': sum(not grounded_claim(c, rows)[0] for c in selected),
        'not_a_semantic_fidelity_measure': True}
    report['operator_vote_records'] = len(state['votes'])
    report['unreviewed_export_error'] = review_error
    report['corrected']['selected_source_time_extent_ms'] = {
        'start': min((by_id[i]['start_ms'] for i in source_ids), default=None),
        'end': max((by_id[i]['end_ms'] for i in source_ids), default=None),
        'not_a_semantic_coverage_score': True}
    execution = results / 'summary-execution.json'
    report['source_hash_scope'] = 'working_tree_at_report_time; executed source hashes provided separately when captured'
    if execution.exists():
        report['summary_execution'] = json.loads(execution.read_text(encoding='utf-8'))
    report['model_manifest_sha256'] = {name: sha256_file(ROOT / name) for name in ('models_manifest.json', 'diarization_models_manifest.json')}
    for stage in ('asr', 'diarization', 'summary'):
        timing = (results if stage == 'summary' else work) / (stage + '-timing.json')
        if timing.exists():
            report[stage + '_timing'] = json.loads(timing.read_text(encoding='utf-8'))
    if args.reference:
        annotations = json.loads(args.reference.read_text(encoding='utf-8'))
        if not annotations.get('segments') or any(not s.get('text', '').strip() or not s.get('speaker') for s in annotations['segments']):
            raise ValueError('EMPTY_OR_INCOMPLETE_HUMAN_REFERENCE')
        report['human_reference'] = 'provided'
        report['human_metrics'] = {'baseline': reference_metrics(annotations, baseline['utterance']), 'corrected': reference_metrics(annotations, rows)}
    atomic_json(args.report, report)
    atomic_json(destination / 'summary-document.json', draft)
    store.close()
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
