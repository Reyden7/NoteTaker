"""Export an explicitly unreviewed working copy, separate from official export."""
from pathlib import Path
import uuid
from .export import _pdf, _docx
from notetaker.domain.minutes import validate_minutes
from notetaker.infrastructure.atomic import atomic_json,sha256_file
from notetaker.infrastructure.paths import session_directory


def export_working_copy(store,sid,destination):
    state=store.get(sid); draft=state['draft']
    if not draft: raise ValueError('Générez un brouillon avant son export.')
    if draft['context_sha256']!=store.context_hash(sid):
        raise ValueError('La séance a changé depuis ce brouillon. Enregistrez les corrections avant de l’exporter.')
    content=draft['content']
    validate_minutes(content,{u['id'] for u in state['utterances']},{v['id']:v for v in state['votes']})
    # Structural citation integrity is mandatory even for an unreviewed copy.
    from .evidence import draft_issues,DraftEvidenceError
    issues=[i for i in draft_issues(content,state) if i['reason'] in {
        'missing_source','missing_evidence','quote_not_in_source','mixed_or_wrong_speaker','source_not_in_point',
        'missing_point_sources','malformed_claim','narrative_missing_claim','narrative_voice_changed','narrative_text_changed'}]
    if issues: raise DraftEvidenceError(issues)
    destination=Path(destination)
    if destination.suffix.lower() not in {'.pdf','.docx'}: raise ValueError('Choisissez un fichier PDF ou DOCX.')
    # Existing renderers already mark preview PDFs on every page. No fake review.
    details={**state['metadata'],'title':state['title'],'preview':True,'working_draft':True}
    directory=session_directory(store.root,sid)/'working-exports';directory.mkdir(exist_ok=True)
    internal=directory/(str(uuid.uuid4())+destination.suffix.lower())
    renderer=_pdf if destination.suffix.lower()=='.pdf' else _docx
    renderer(content,'BROUILLON NON RELU — NON OFFICIEL',internal,state['votes'],state['decisions'],details)
    destination.parent.mkdir(parents=True,exist_ok=True)
    import shutil, tempfile, os
    fd,name=tempfile.mkstemp(dir=destination.parent,suffix='.part')
    try:
        with os.fdopen(fd,'wb') as target,internal.open('rb') as source:
            shutil.copyfileobj(source,target);target.flush();os.fsync(target.fileno())
        os.replace(name,destination)
    finally:Path(name).unlink(missing_ok=True)
    atomic_json(internal.with_suffix('.snapshot.json'),{'status':'unreviewed-working-copy','session_id':sid,
        'draft_id':draft['id'],'sha256':sha256_file(internal),'content':content})
    return destination
