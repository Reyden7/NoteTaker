"""The model cannot approve a draft or add vote results to structured inputs."""
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files

SCHEMA = json.loads(files("notetaker").joinpath("schemas/minutes.json").read_text(encoding="utf-8"))

def validate_minutes(content: dict, segment_ids: set[str], recorded_votes: dict) -> None:
    from jsonschema import Draft202012Validator
    Draft202012Validator(SCHEMA).validate(content)
    for point in content["points"]:
        if not set(point["sources"]) <= segment_ids:
            raise ValueError("UNKNOWN_SOURCE_SEGMENT")
        vote_id = point["vote_id"]
        if vote_id is not None and vote_id not in recorded_votes:
            raise ValueError("UNKNOWN_STRUCTURED_VOTE")
        for claim in point.get("claims", []):
            if not claim.get("evidence") or not {e["id"] for e in claim["evidence"]} <= set(point["sources"]):
                raise ValueError("CLAIM_SOURCES_NOT_IN_POINT")
    # No numeric vote values are accepted in model output. Rendering will use
    # operator-entered vote objects later. Free text still needs human checking.

def content_digest(content: dict) -> str:
    data = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class HumanReview:
    content_sha256: str
    reviewer: str
    reviewed_at: str

def record_human_review(content: dict, reviewer: str) -> HumanReview:
    if not reviewer.strip():
        raise ValueError("REVIEWER_REQUIRED")
    return HumanReview(content_digest(content), reviewer, datetime.now(timezone.utc).isoformat())

def require_review(content: dict, review: HumanReview | None) -> None:
    if review is None or not review.reviewer.strip() or review.content_sha256 != content_digest(content):
        raise ValueError("HUMAN_REVIEW_REQUIRED_FOR_THIS_REVISION")
