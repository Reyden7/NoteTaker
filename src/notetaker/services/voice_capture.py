"""Microphone references encrypted block by block; no plaintext audio journal."""
import queue
import threading


class EncryptedVoiceCapture:
    def __init__(self,vault,person_id):
        self.vault,self.pid=vault,person_id
        self.queue=queue.Queue(maxsize=256);self.finished=threading.Event()
        self.frames=0;self.error='';self.stream=None;self.thread=None;self.sample_id=None

    def start(self,device_id):
        import sounddevice as sd
        self.sample_id=self.vault.begin(self.pid)
        def callback(data,frames,timestamp,status):
            if status or self.frames+frames>90*16000:
                self.error='Niveau d’entrée instable ou durée maximale de 90 secondes atteinte.'
                raise sd.CallbackStop()
            try: self.queue.put_nowait(bytes(data));self.frames+=frames
            except queue.Full:
                self.error='Écriture du coffre trop lente. La prise déjà chiffrée reste conservée.'
                raise sd.CallbackStop()
        def writer():
            try:
                while not self.finished.is_set() or not self.queue.empty():
                    try: data=self.queue.get(timeout=.1)
                    except queue.Empty: continue
                    self.vault.append(self.sample_id,data)
            except Exception as error: self.error=str(error)
        self.thread=threading.Thread(target=writer,name='notetaker-encrypted-voice',daemon=False);self.thread.start()
        try:
            self.stream=sd.RawInputStream(device=device_id,samplerate=16000,channels=1,dtype='int16',blocksize=2048,callback=callback)
            self.stream.start()
        except BaseException:
            self.stop();raise

    def stop(self):
        if self.stream:
            try: self.stream.stop()
            finally: self.stream.close();self.stream=None
        self.finished.set()
        if self.thread:
            self.thread.join(timeout=10)
            if self.thread.is_alive(): raise RuntimeError('Attendez la fin de l’écriture chiffrée avant de fermer.')
        if self.sample_id:
            with self.vault.connection() as db:
                db.execute("UPDATE sample SET state='pending' WHERE id=? AND state='capturing'",(self.sample_id,))


def import_voice(vault,pid,path):
    vault.require_authorization()
    from pathlib import Path
    path=Path(path).resolve(strict=True)
    if not path.is_file() or path.suffix.lower() not in {'.wav','.mp3','.m4a'}:
        raise ValueError('Choisissez un fichier vocal local WAV, MP3 ou M4A.')
    import av
    pcm=bytearray()
    converter=av.AudioResampler(format='s16',layout='mono',rate=16000)
    def append(frames):
        for frame in frames:
            pcm.extend(bytes(frame.planes[0])[:frame.samples*2])
            if len(pcm)>90*16000*2: raise ValueError('Importez un échantillon de 90 secondes maximum, sans modifier votre fichier original.')
    with av.open(str(path)) as container:
        for frame in container.decode(audio=0): append(converter.resample(frame))
    append(converter.resample(None))
    if len(pcm)<30*16000*2: raise ValueError('Au moins 30 secondes sont nécessaires pour une prise de référence.')
    sid=vault.begin(pid)
    try:
        for index in range(0,len(pcm),32000): vault.append(sid,bytes(pcm[index:index+32000]))
        with vault.connection() as db: db.execute("UPDATE sample SET state='pending' WHERE id=?",(sid,))
    except BaseException: vault.delete(pid,sid);raise
    return sid
