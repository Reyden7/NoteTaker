"""A missing, changed, or legally unapproved asset blocks use; no downloader."""
import re
from pathlib import Path
from .atomic import sha256_file

def verify_assets(root: Path, entries: list[dict], *, release: bool = False) -> None:
    if not entries:
        raise ValueError("EMPTY_ASSET_MANIFEST")
    root = root.resolve(strict=True)
    seen = set()
    for item in entries:
        relative = Path(item["path"])
        if relative.is_absolute() or relative.drive or ".." in relative.parts:
            raise ValueError("UNSAFE_ASSET_PATH")
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("UNSAFE_ASSET_PATH")
        key = str(path).casefold()
        if key in seen:
            raise ValueError("DUPLICATE_ASSET")
        seen.add(key)
        if not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise ValueError("INVALID_ASSET_HASH")
        if path.stat().st_size != item["size_bytes"] or sha256_file(path) != item["sha256"]:
            raise ValueError("ASSET_INTEGRITY_FAILED")
        if release and (item.get("redistribution") != "approved" or not item.get("license_notice")):
            raise ValueError("REDISTRIBUTION_NOT_APPROVED")
