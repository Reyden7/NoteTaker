"""Configure the desktop media backend before Qt Multimedia is initialized."""
import os
import sys


def configure_media_backend():
    # Qt 6.8 FFmpeg fails to initialize SWR for some Windows surround outputs
    # (reproduced with Logitech PRO X 7.1). Media Foundation handles this device.
    # This is process-local; it does not affect PyAV, ASR workers or Windows settings.
    if sys.platform == 'win32':
        os.environ['QT_MEDIA_BACKEND'] = 'windows'
