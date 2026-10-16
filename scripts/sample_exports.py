"""Technical export fixture, NOT an operator-validated meeting document."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from notetaker.domain.minutes import HumanReview, content_digest
from notetaker.services.export import export_draft

content = {
    "points": [{"title": "Vérification des exports locaux",
                "summary": "Échantillon technique de phase 0 avec données fictives. Ce document teste les accents français, la pagination et les mentions de brouillon. Il ne décrit aucune séance réelle.",
                "sources": ["fixture-1"], "vote_id": None}],
    "to_verify": ["Le contrôle humain dans l’interface reste à développer.", "Aucun vote n’a été fourni dans cet échantillon."]}
# Test fixture only: never use this construction in an operator workflow.
review = HumanReview(content_digest(content), "AUTOMATED TEST FIXTURE", "2026-10-16T00:00:00Z")
for suffix in ["docx", "pdf"]:
    path = ROOT / f"output/phase0/export-fixture.{suffix}"
    export_draft(content, review, path, session_id="FIXTURE-PHASE0", municipality="Commune fictive", session_date="16 octobre 2026")
    print(path)
