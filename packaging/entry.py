"""Shared frozen entry point: console worker and windowed desktop executable."""
import sys
from pathlib import Path
from notetaker.infrastructure.offline import enforce_offline
enforce_offline()
if Path(sys.executable).stem.lower().endswith("-worker"):
    from notetaker.workers.probe import main
else:
    from notetaker.main import main
raise SystemExit(main())
