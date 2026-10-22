"""Read-only, sample-bounded PCM playback copies. Never edit source metadata."""
from pathlib import Path
import wave


def write_playback_excerpt(source: Path, target: Path, start_ms: int, end_ms: int):
    if not isinstance(start_ms, int) or not isinstance(end_ms, int) or start_ms < 0 or end_ms <= start_ms:
        raise ValueError('Ce passage ne possède pas de durée audio positive. Sélectionnez un autre passage ou vérifiez ses horaires.')
    source = Path(source).resolve(strict=True)
    target = Path(target).resolve()
    if source == target:
        raise ValueError('La copie de lecture doit être distincte de l’enregistrement source.')
    try:
        with wave.open(str(source), 'rb') as audio:
            channels, width, rate, frames, compression, _ = audio.getparams()
            if compression != 'NONE' or width != 2 or channels not in (1, 2):
                raise ValueError('La lecture d’un passage nécessite un WAV PCM 16 bits mono ou stéréo. Le fichier audio préparé est incompatible.')
            # Half-open [start, end), quantized down to the source sample grid.
            # No resampling, padding, clamping or modification of saved timestamps.
            first, last = start_ms * rate // 1000, end_ms * rate // 1000
            if last > frames or last <= first:
                raise ValueError('Les horaires du passage dépassent le fichier audio ou ne contiennent aucun échantillon. Vérifiez la source associée.')
            audio.setpos(first)
            try:
                with wave.open(str(target), 'wb') as out:
                    out.setparams((channels, 2, rate, 0, 'NONE', 'not compressed'))
                    remaining = last - first
                    while remaining:
                        count = min(remaining, 65536)
                        data = audio.readframes(count)
                        if len(data) != count * channels * 2:
                            raise ValueError('Le fichier audio est tronqué. Utilisez une copie complète de la source.')
                        out.writeframesraw(data)
                        remaining -= count
            except Exception:
                target.unlink(missing_ok=True)
                raise
    except (wave.Error, EOFError) as error:
        raise ValueError('Le WAV associé est illisible. Vérifiez le fichier audio préparé, sans modifier l’original.') from error
    return {'start_ms': start_ms, 'end_ms': end_ms, 'rate': rate, 'channels': channels,
            'first_frame': first, 'last_frame': last, 'frames': last-first}
