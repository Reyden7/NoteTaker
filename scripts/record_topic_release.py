"""Bind the development bundle to actual tests and the unreviewed comparison."""
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json,sha256_file
from notetaker import __version__

bundle=ROOT/'dist/topic-summary/NoteTaker';evidence=ROOT/'docs/evidence'
read=lambda name:json.loads((evidence/name).read_text(encoding='utf-8-sig'))
workers=read('bundle-topic-summary.json');desktop=read('desktop-topic-summary.json')
native_previous=read('bundle-topic-before-stance-guard.json')
comparison=read('topic-summary-standard.json');review=read('topic-review-copy.json')
pdf=read('topic-comparison-pdf.json');native=read('native-payload-topic-summary.json')
tests=ET.parse(evidence/'pytest-topic-summary.xml').getroot().find('testsuite').attrib
assert tests['failures']==tests['errors']=='0'
assert comparison['status']=='passed' and comparison['snapshot_unchanged']
assert not comparison['human_review_created'] and not comparison['production_export_performed']
assert review['production_export_without_review_blocked'] and review['original_snapshot_unchanged']
assert pdf['rendered_pages_visually_inspected'] and not pdf['replacement_characters']
assert sha256_file(Path(pdf['pdf']))==pdf['sha256']
assert desktop['responsive_main_window'] and desktop['graceful_exit']
assert not native['forbidden_optional_files']
for name,digest in workers['executables_sha256'].items():assert sha256_file(bundle/name)==digest
assert desktop['executable_sha256']==workers['executables_sha256']['NoteTaker.exe']
assert all(w['exit_code']==0 and w['response']['status']=='completed' for w in workers['workers'].values())
for name,digest in comparison['source_sha256'].items():assert sha256_file(ROOT/name)==digest
archive=CArchiveReader(str(bundle/'NoteTaker.exe')).open_embedded_archive('PYZ.pyz')
modules=['notetaker.engines.topic_summary','notetaker.domain.summary','notetaker.services.pipeline',
    'notetaker.services.evidence','notetaker.ui.window','notetaker.ui.evidence']
for name in modules:
    compiled=archive.extract(name)
    source=ROOT/'src'/Path(name.replace('.','/')).with_suffix('.py')
    assert compiled==compile(source.read_text(encoding='utf-8'),compiled.co_filename,'exec',dont_inherit=True,optimize=0),name
assert sha256_file(ROOT/'docs/operator-guide.md')==sha256_file(bundle/'GUIDE-UTILISATEUR.md')
report={'version':__version__,'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
    'bundle':str(bundle),'executables_sha256':workers['executables_sha256'],
    'tests_passed':int(tests['tests']),'compiled_workers_passed':list(workers['workers']),
    'final_llm_native_calls':workers['workers']['llm'].get('native_calls_executed_this_run'),
    'final_llm_cache_identities_at_start':workers['workers']['llm'].get('native_cache_identities_at_start'),
    'previous_fresh_native_llm_seconds':native_previous['workers']['llm']['seconds'],
    'previous_fresh_native_evidence':'bundle-topic-before-stance-guard.json',
    'compiled_ui_started_closed':True,'frozen_modules_equal_current_sources':modules,
    'comparison_status':comparison['status'],'comparison_transcription_rows':comparison['transcription_rows'],
    'comparison_pdf_sha256':pdf['sha256'],'comparison_pdf_pages_inspected':pdf['pages'],
    'unreviewed_production_export_blocked':True,'real_meeting_review_created':False,
    'human_fidelity_improvement_measured':None,'biometric_identification_added':False,
    'clean_offline_windows_validated':False,'commercial_installer_validated':False,
    'native_redistribution_clearance':False,'environment':workers['environment']}
atomic_json(evidence/'topic-summary-release.json',report)
print(json.dumps(report,ensure_ascii=True,indent=2))
