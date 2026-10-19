"""Record verified build identities and distinguish each acceptance scope."""
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json,sha256_file
from notetaker import __version__

bundle=ROOT/'dist/validation-fixes/NoteTaker'
evidence=ROOT/'docs/evidence'
read=lambda name:json.loads((evidence/name).read_text(encoding='utf-8-sig'))
workers=read('bundle-validation-fixes.json')
desktop=read('desktop-validation-fixes.json')
chain=read('corrections-real-workers-chain.json')
audit=read('validation-fix-real-audit.json')
native=read('native-payload-validation-fixes.json')
tests=ET.parse(evidence/'pytest-validation-fixes.xml').getroot().find('testsuite').attrib
assert tests['failures']==tests['errors']=='0'
for name,digest in workers['executables_sha256'].items():assert sha256_file(bundle/name)==digest
assert desktop['executable_sha256']==workers['executables_sha256']['NoteTaker.exe']
assert desktop['responsive_main_window'] and desktop['graceful_exit']
assert all(w['exit_code']==0 and w['response']['status']=='completed' for w in workers['workers'].values())
assert chain['status']=='passed' and not chain['human_review_of_real_meeting']
assert not audit['review_created'] and audit['invalid_links_after_proposed_attribution_refresh']==0
assert audit['original_snapshot_unchanged'] and audit['unreviewed_export_blocked']
assert not native['forbidden_optional_files']
archive=CArchiveReader(str(bundle/'NoteTaker.exe')).open_embedded_archive('PYZ.pyz')
modules=['notetaker.services.evidence','notetaker.services.transcript','notetaker.ui.evidence']
assert all(name in archive.toc for name in modules)
guide=ROOT/'docs/operator-guide.md'
assert sha256_file(guide)==sha256_file(bundle/'GUIDE-UTILISATEUR.md')
sources=['src/notetaker/services/storage.py','src/notetaker/services/evidence.py',
    'src/notetaker/services/transcript.py','src/notetaker/services/pipeline.py',
    'src/notetaker/engines/hierarchical_summary.py','src/notetaker/ui/window.py','src/notetaker/ui/evidence.py']
report={'version':__version__,'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
    'bundle':str(bundle),'executables_sha256':workers['executables_sha256'],
    'bundle_size_bytes':sum(p.stat().st_size for p in bundle.rglob('*') if p.is_file()),
    'unit_and_widget_tests_passed':int(tests['tests']),'compiled_workers_passed':list(workers['workers']),
    'compiled_ui_startup_shutdown':True,'new_modules_in_frozen_archive':modules,
    'source_hashes':{name:sha256_file(ROOT/name) for name in sources},
    'bundled_guide_sha256':sha256_file(guide),
    'real_snapshot_proposal_invalid_links_before':audit['invalid_source_links_before'],
    'real_snapshot_proposal_invalid_links_after':0,'real_meeting_automatically_approved':False,
    'synthetic_source_chain_passed':True,'synthetic_chain_seconds':chain['wall_seconds'],
    'visual_export_qa':{'scope':'known synthetic fixture only','pdf_pages_inspected':2,
        'docx_rendered_pages_inspected':2,'renderer':'Poppler and installed Word read-only; not a product dependency',
        'observed_layout_defects':False},
    'natural_speaker_precision_measured':False,'natural_semantic_fidelity_measured':False,
    'biometric_identification_added':False,'clean_offline_windows_validated':False,
    'commercial_installer_validated':False,'environment':workers['environment']}
atomic_json(evidence/'validation-fixes-release.json',report)
print(json.dumps(report,ensure_ascii=True,indent=2))
