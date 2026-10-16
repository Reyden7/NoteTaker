from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class Attempt:
    device: str
    ok: bool
    error_code: str | None = None

@dataclass(frozen=True)
class RoutedResult:
    value: dict
    device: str
    attempts: tuple[Attempt, ...]

class EngineUnavailable(RuntimeError):
    def __init__(self, attempts):
        self.attempts = tuple(attempts)
        super().__init__("ALL_ENGINE_ATTEMPTS_FAILED")

def run_with_fallback(run: Callable[[str], dict], mode: str = "auto") -> RoutedResult:
    """run executes a representative task in a FRESH process per attempt.

    Never catch cancellation (KeyboardInterrupt/SystemExit). CPU failure is an error.
    Each engine has its own call; inventory alone never authorizes GPU selection.
    """
    if mode not in {"auto", "cpu", "gpu"}:
        raise ValueError("INVALID_ENGINE_MODE")
    attempts = []
    for device in (["cpu"] if mode == "cpu" else ["cuda", "cpu"]):
        try:
            value = run(device)
        except (RuntimeError, OSError, TimeoutError) as exc:
            # Never log exception text: it can contain transcript, paths or names.
            attempts.append(Attempt(device, False, type(exc).__name__))
        else:
            attempts.append(Attempt(device, True))
            return RoutedResult(value, device, tuple(attempts))
    raise EngineUnavailable(attempts)
