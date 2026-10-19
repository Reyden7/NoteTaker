"""Bind development binaries to sources and actual evidence; never approve a meeting."""
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker import __version__
from notetaker.infrastructure.atomic import atomic_json, sha256_file

bundle = ROOT / 'dist/information-registry/NoteTaker'
evidence = ROOT / 'docs/evidence'
read = lambda name: json.loads((evidence / name).read_text(encoding='utf-8-sig'))
tests = ET.parse(evidence / 'pytest-information-registry.xml').getroot().find('testsuite').attrib
assert tests['failures'] == tests['errors'] == tests['skipped'] == '0'
desktop = read('desktop-information-registry.json')
native = read('information-registry-native-request.json')
audio = read('information-registry-audio-engines-unchanged.json')
ui = read('information-registry-ui.json')
field_ui = read('information-registry-field-ui.json')
comparison = read('information-registry-real-comparison.json')
post = read('information-registry-post-writing-observations.json')
assert desktop['responsive_main_window'] and desktop['graceful_exit']
assert native['status'] == 'passed' and native['source_rows_unchanged'] and native['historical_reviews_unchanged']
assert native['python_network_attempts'] == 0 and not native['human_review_created']
assert ui['visually_inspected']
assert field_ui['visually_inspected'] and field_ui['source_draft_reviews_unchanged']
assert field_ui['source_rows'] == 670 and not field_ui['human_review_created']
assert comparison['status'] == 'passed'
assert comparison['transcription_rows'] == 670
assert comparison['original_snapshot_unchanged'] and comparison['copied_transcription_unchanged']
assert comparison['historical_draft_preserved'] and comparison['production_export_without_review_blocked']
assert not comparison['human_review_created'] and not comparison['human_reference_available']
assert post['source_rows_unchanged'] and post['historical_reviews_unchanged']
assert post['comparison_draft_retained'] and post['comparison_draft_obsolete_after_doubts']
assert post['obsolete_draft_reference_preflight_refused']
assert not post['human_review_created']
assert sha256_file(evidence / 'information-registry-real-comparison.json') == sha256_file(
    ROOT / 'output/information-registry/field-670/comparison.json')
for name, digest in comparison['source_sha256'].items():
    assert sha256_file(ROOT / name) == digest
assert all(audio['audio_functions_unchanged'].values()) and all(audio['audio_modules_unchanged'].values())
assert sha256_file(ROOT / 'dist/topic-summary/NoteTaker/NoteTaker-worker.exe') == audio['baseline_worker_sha256']
assert sha256_file(bundle / 'NoteTaker.exe') == desktop['executable_sha256']
assert sha256_file(bundle / 'NoteTaker-worker.exe') == native['frozen_worker_sha256']
modules = ['notetaker.domain.information_registry', 'notetaker.engines.registry_summary',
    'notetaker.engines.topic_summary', 'notetaker.engines.hierarchical_summary',
    'notetaker.services.information_registry', 'notetaker.services.pipeline',
    'notetaker.services.storage', 'notetaker.services.evidence',
    'notetaker.ui.window', 'notetaker.ui.information_registry',
    'notetaker.workers.probe', 'notetaker.domain.summary', 'notetaker.infrastructure.database']
for binary in ['NoteTaker.exe', 'NoteTaker-worker.exe']:
    archive = CArchiveReader(str(bundle / binary)).open_embedded_archive('PYZ.pyz')
    for name in modules:
        compiled = archive.extract(name)
        source = ROOT / 'src' / Path(name.replace('.', '/')).with_suffix('.py')
        assert compiled == compile(source.read_text(encoding='utf-8'), compiled.co_filename,
            'exec', dont_inherit=True, optimize=0), (binary, name)
for source, shipped in [('docs/operator-guide.md', 'GUIDE-UTILISATEUR.md'),
    ('docs/information-registry-0.2.4.md', 'REGISTRE-INFORMATIONS.md')]:
    assert sha256_file(ROOT / source) == sha256_file(bundle / shipped)
assert sha256_file(ROOT / 'src/notetaker/schemas/minutes.json') == sha256_file(
    bundle / '_internal/notetaker/schemas/minutes.json')
report = {'version': __version__, 'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
    'bundle': str(bundle), 'tests_passed': int(tests['tests']),
    'executables_sha256': {name: sha256_file(bundle / name) for name in ['NoteTaker.exe', 'NoteTaker-worker.exe']},
    'frozen_modules_equal_current_sources_in_both_binaries': modules,
    'compiled_ui_started_closed': True, 'compiled_information_check_native_calls': native['native_calls'],
    'compiled_information_check_seconds': native['seconds'], 'real_meeting_review_created': False,
    'final_information_check_native_cache_hits': native.get('native_cache_hits', 0),
    'earlier_fresh_compiled_check_native_calls': native.get('previous_fresh_native_calls'),
    'earlier_fresh_compiled_check_seconds': native.get('previous_fresh_seconds'),
    'real_copy_ui_opened_and_inspected': True,
    'audio_scope_evidence': 'information-registry-audio-engines-unchanged.json',
    'source_comparison_evidence': 'information-registry-real-comparison.json',
    'source_comparison_status': comparison['status'],
    'real_comparison_paragraphs': comparison['new_paragraphs'],
    'real_comparison_written_information': comparison['written_information'],
    'post_writing_doubts': len(post['observations']),
    'current_information_to_verify': post['current_coverage']['to_verify_information_entries'],
    'comparison_draft_obsolete_after_development_doubts': True,
    'unreviewed_production_export_blocked': True,
    'human_fidelity_improvement_measured': None, 'biometric_identification_added': False,
    'clean_offline_windows_validated': False, 'commercial_installer_validated': False,
    'native_redistribution_clearance': False,
    'environment': 'developer PC; not clean Windows; host not disconnected'}
atomic_json(evidence / 'information-registry-release.json', report)
print(json.dumps(report, ensure_ascii=True, indent=2))
