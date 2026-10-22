"""Opt-in voice references, encrypted at rest; no learning from session edits."""
import contextlib
import json
import sqlite3
import uuid
import time
from datetime import date, timedelta
from pathlib import Path
from notetaker.infrastructure.voice_vault import protect, unprotect
from notetaker.infrastructure.atomic import sha256_file


class VoiceProfiles:
    def __init__(self, root, *, encrypt=protect, decrypt=unprotect):
        self.path = Path(root)/'voice-vault.sqlite3'
        self.encrypt, self.decrypt = encrypt,decrypt
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connection() as db:
            db.executescript('CREATE TABLE IF NOT EXISTS policy(id INTEGER PRIMARY KEY, payload BLOB NOT NULL);'
                'CREATE TABLE IF NOT EXISTS sample(id TEXT PRIMARY KEY, person_id TEXT NOT NULL, created TEXT NOT NULL, expires TEXT NOT NULL, state TEXT NOT NULL, rate INTEGER NOT NULL, channels INTEGER NOT NULL, embedding BLOB);'
                'CREATE TABLE IF NOT EXISTS block(sample_id TEXT NOT NULL REFERENCES sample(id) ON DELETE CASCADE, seq INTEGER NOT NULL, payload BLOB NOT NULL, PRIMARY KEY(sample_id,seq));')

    @contextlib.contextmanager
    def connection(self):
        db=sqlite3.connect(self.path,timeout=30)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON'); db.execute('PRAGMA secure_delete=ON')
        try:
            with db: yield db
        finally: db.close()

    def policy(self):
        with self.connection() as db: row=db.execute('SELECT payload FROM policy WHERE id=1').fetchone()
        return json.loads(self.decrypt(row[0])) if row else {'enabled':False}

    def configure(self, policy):
        if policy.get('enabled'):
            if not all(str(policy.get(k,'')).strip() for k in ('legal_reference','authorized_by','expires','retention_days')):
                raise ValueError('Renseignez l’autorisation juridique, le responsable, l’échéance et la conservation avant activation.')
            try:expires=date.fromisoformat(policy['expires'])
            except ValueError as error:raise ValueError('La date d’autorisation doit être au format AAAA-MM-JJ.') from error
            if expires < date.today() or not 1 <= int(policy['retention_days']) <= 3650:
                raise ValueError('Autorisation expirée ou durée de conservation invalide.')
            if not 0 < float(policy.get('threshold',.8)) <= 1 or not 0 < float(policy.get('margin',.12)) <= 1:
                raise ValueError('Seuil ou marge de correspondance invalide.')
        blob=self.encrypt(json.dumps(policy,ensure_ascii=False).encode('utf-8'))
        with self.connection() as db: db.execute('INSERT OR REPLACE INTO policy VALUES(1,?)',(blob,))

    def require_authorization(self):
        policy=self.policy()
        if not policy.get('enabled') or date.fromisoformat(policy['expires']) < date.today():
            raise ValueError('Identification vocale désactivée : une autorisation juridique de la collectivité en cours de validité est requise.')
        return policy

    def begin(self, person_id, rate=16000, channels=1):
        policy=self.require_authorization(); uuid.UUID(person_id)
        if (rate,channels)!=(16000,1):raise ValueError('Les références vocales utilisent du PCM mono à 16 kHz.')
        sid=str(uuid.uuid4())
        with self.connection() as db:
            db.execute('INSERT INTO sample VALUES(?,?,?,?,?,?,?,?)',
                (sid,person_id,date.today().isoformat(),(date.today()+timedelta(days=int(policy['retention_days']))).isoformat(),'capturing',rate,channels,None))
        return sid

    def append(self,sid,pcm):
        self.require_authorization()
        blob=self.encrypt(pcm)
        with self.connection() as db:
            row=db.execute('SELECT state FROM sample WHERE id=?',(sid,)).fetchone()
            if not row or row[0]!='capturing': raise ValueError('La prise vocale n’est plus ouverte.')
            seq=db.execute('SELECT coalesce(max(seq),-1)+1 FROM block WHERE sample_id=?',(sid,)).fetchone()[0]
            db.execute('INSERT INTO block VALUES(?,?,?)',(sid,seq,blob))

    def samples(self,pid=None):
        with self.connection() as db:
            rows=db.execute('SELECT id,person_id,created,expires,state,rate,channels FROM sample'+(' WHERE person_id=?' if pid else ''), (pid,) if pid else ()).fetchall()
        return [dict(r) for r in rows]

    def pcm(self,sid):
        self.require_authorization()
        with self.connection() as db:
            row=db.execute('SELECT expires FROM sample WHERE id=?',(sid,)).fetchone()
            if not row or row[0]<date.today().isoformat(): raise ValueError('Échantillon absent ou expiré.')
            blobs=db.execute('SELECT payload FROM block WHERE sample_id=? ORDER BY seq',(sid,)).fetchall()
        return b''.join(self.decrypt(r[0]) for r in blobs)

    def finish(self,sid,reference):
        self.require_authorization()
        blob=self.encrypt(json.dumps(reference,allow_nan=False).encode('utf-8'))
        with self.connection() as db: db.execute("UPDATE sample SET state='ready',embedding=? WHERE id=?",(blob,sid))

    def references(self,model_hash):
        self.require_authorization(); result={}
        with self.connection() as db:
            rows=db.execute("SELECT person_id,embedding FROM sample WHERE state='ready' AND expires>=?",(date.today().isoformat(),)).fetchall()
        for row in rows:
            data=json.loads(self.decrypt(row['embedding']))
            if data.get('model_hash')==model_hash and data.get('preprocessing')=='pcm16-mono-16000-v1':
                result.setdefault(row['person_id'],[]).extend(data['vectors'])
        return result

    def delete(self,pid,sample_id=None):
        # Deletion remains available after revocation or expiration.
        with self.connection() as db:
            db.execute('DELETE FROM sample WHERE person_id=?'+(' AND id=?' if sample_id else ''),(pid,sample_id) if sample_id else (pid,))

    def purge_expired(self):
        with self.connection() as db: return db.execute('DELETE FROM sample WHERE expires<?',(date.today().isoformat(),)).rowcount


def normalized(vector):
    import numpy as np
    v=np.asarray(vector,dtype=np.float32)
    norm=np.linalg.norm(v)
    if v.ndim!=1 or not np.isfinite(v).all() or norm<1e-8: raise ValueError('Empreinte vocale invalide.')
    return v/norm


def rank_voice(vectors,references,threshold=.8,margin=.12):
    """Thresholds are policy settings, not calibrated probabilities."""
    import numpy as np
    if not vectors or not references: return {'status':'not_identified'}
    prototypes={pid:normalized(np.mean([normalized(v) for v in rows],axis=0)) for pid,rows in references.items() if rows}
    observations=[]
    for vector in vectors:
        vector=normalized(vector)
        scores=sorted(((float(vector @ p),pid) for pid,p in prototypes.items()),reverse=True)
        if not scores: return {'status':'not_identified'}
        score,pid=scores[0]; gap=score-scores[1][0] if len(scores)>1 else score
        observations.append((pid,score,gap))
    if any(score<threshold for _,score,_ in observations): return {'status':'not_identified'}
    if len(observations)<2 or len({pid for pid,_,_ in observations})!=1 or any(gap<margin for _,_,gap in observations):
        return {'status':'uncertain','reason':'Marge, durée ou cohérence insuffisante.'}
    return {'status':'suggested','person_id':observations[0][0],
        'score':min(s for _,s,_ in observations),'margin':min(m for _,_,m in observations)}


def extract_vectors(samples,model,cancel=None,extractor=None):
    import numpy as np
    import sherpa_onnx as s
    from notetaker.infrastructure.process import JobCancelled
    engine=extractor or s.SpeakerEmbeddingExtractor(s.SpeakerEmbeddingExtractorConfig(model=str(model),num_threads=4,provider='cpu'))
    vectors=[]
    for start in range(0,len(samples),4*16000):
        if cancel is not None and cancel.is_set(): raise JobCancelled('JOB_CANCELLED')
        data=samples[start:start+4*16000]
        if len(data)<2*16000 or np.sqrt(np.mean(data**2))<.005: continue
        stream=engine.create_stream();stream.accept_waveform(16000,data);stream.input_finished()
        if engine.is_ready(stream): vectors.append(normalized(engine.compute(stream)).tolist())
    return vectors


def verify_voice_models(models):
    from notetaker.infrastructure.models import verify_assets
    root=Path(models.root).resolve()
    expected={Path(p).resolve().relative_to(root).as_posix() for p in (models.segmentation,models.refinement_embedding)}
    manifest=json.loads((root/'diarization_models_manifest.json').read_text(encoding='utf-8'))
    entries=[item for item in manifest['assets'] if item['path'] in expected]
    if len(entries)!=2:raise ValueError('Les modèles vocaux ne sont pas décrits par le manifeste local vérifié.')
    verify_assets(root,entries)


def enroll(vault,sample_id,models,cancel=None):
    import numpy as np
    import sherpa_onnx as s
    vault.require_authorization();verify_voice_models(models)
    pcm=vault.pcm(sample_id); samples=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
    if not 30*16000 <= len(samples) <= 90*16000: raise ValueError('Enregistrez 30 à 60 secondes, au maximum 90 secondes par prise.')
    if np.mean(np.abs(samples)>=.99)>.01: raise ValueError('Enregistrement saturé : réduisez le niveau du microphone et recommencez.')
    config=s.OfflineSpeakerDiarizationConfig(segmentation=s.OfflineSpeakerSegmentationModelConfig(
        pyannote=s.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(models.segmentation)),num_threads=4,provider='cpu'),
        embedding=s.SpeakerEmbeddingExtractorConfig(model=str(models.refinement_embedding),num_threads=4,provider='cpu'),
        clustering=s.FastClusteringConfig(num_clusters=-1,threshold=.4))
    diar=s.OfflineSpeakerDiarization(config)
    turns=diar.process(samples).sort_by_start_time()
    if len({t.speaker for t in turns})!=1: raise ValueError('Aucune voix unique exploitable : silence ou plusieurs voix possibles. Recommencez dans un endroit calme.')
    from notetaker.engines.overlap import possible_overlaps
    from notetaker.engines.speaker_refinement import clean_intervals
    overlaps=possible_overlaps(samples,models.segmentation)
    intervals=[(a,b) for t in turns for a,b in clean_intervals(t.start,t.end,overlaps) if b-a>=2]
    seconds=sum(b-a for a,b in intervals)
    if seconds<20: raise ValueError('Moins de 20 secondes de parole sans chevauchement sont exploitables. Faites une nouvelle prise.')
    vectors=[]
    for a,b in intervals: vectors.extend(extract_vectors(samples[round(a*16000):round(b*16000)],models.refinement_embedding,cancel))
    if len(vectors)<3: raise ValueError('Trop peu de fenêtres vocales exploitables. Recommencez.')
    result={'model_hash':sha256_file(models.refinement_embedding),'preprocessing':'pcm16-mono-16000-v1',
        'dimension':len(vectors[0]),'vectors':vectors,'speech_seconds':seconds,'overlap_intervals':len(overlaps),
        'quality_human_confirmed':False}
    vault.finish(sample_id,result)
    return {k:v for k,v in result.items() if k!='vectors'}


def identify_session(store,state,models,cancel=None):
    import numpy as np
    import wave
    from .directory import DirectoryService,person_name
    try:
        vault=VoiceProfiles(store.root);vault.purge_expired()
        if not vault.policy().get('enabled'): return {'status':'disabled','labels':{}}
        policy=vault.require_authorization()
        if not policy.get('calibration_reference'):
            return {'status':'not_calibrated','labels':{},'warning':'Identification nominative non appliquée : seuils non calibrés sur des références humaines indépendantes.'}
        verify_voice_models(models)
        references=vault.references(sha256_file(models.refinement_embedding))
        active={p['id']:p for p in DirectoryService(store).list_people()}
        participants={p['person_id'] for p in state['participants'] if p['attendance'] in ('present','unconfirmed')}
        references={pid:rows for pid,rows in references.items() if pid in active and (not participants or pid in participants)}
        if not references:
            return {'status':'no_compatible_profiles','labels':{},'warning':'Aucune référence vocale compatible et autorisée. Vérifiez les participants, la conservation et le modèle ; un nouvel enrôlement peut être nécessaire.'}
        import sherpa_onnx as s
        extractor=s.SpeakerEmbeddingExtractor(s.SpeakerEmbeddingExtractorConfig(model=str(models.refinement_embedding),num_threads=4,provider='cpu'))
        matches,labels={},{}
        from notetaker.domain.summary import voice_registry
        known_voices=voice_registry(state)
        for speaker in state['speakers']:
            vault.require_authorization()
            if known_voices.get(speaker,{}).get('confirmed'):
                matches[speaker]={'status':'human_attribution_preserved'}
                continue
            vectors=[]
            for row in state['utterances']:
                source=json.loads(row['source_json'])
                if row['speaker_id']!=speaker or source.get('automatic_attribution') is False or source.get('possible_overlap') or source.get('simultaneous_turns'):
                    continue
                if row['end_ms']-row['start_ms']<2000: continue
                with wave.open(source['normalized_audio'],'rb') as audio:
                    if (audio.getnchannels(),audio.getsampwidth(),audio.getframerate())!=(1,2,16000): raise ValueError('Audio normalisé incompatible avec les références vocales.')
                    audio.setpos(row['start_ms']*16)
                    data=np.frombuffer(audio.readframes((row['end_ms']-row['start_ms'])*16),dtype='<i2').astype(np.float32)/32768
                vectors.extend(extract_vectors(data,models.refinement_embedding,cancel,extractor))
            match=rank_voice(vectors,references,float(policy.get('threshold',.8)),float(policy.get('margin',.12)))
            matches[speaker]=match
            if match['status']=='suggested': labels[speaker]=person_name(active[match['person_id']])
        # No session labels, human edits, speaker boundaries or reference samples are changed.
        vault.require_authorization()
        return {'status':'suggestions','matches':matches,'labels':labels,
            'warning':'Correspondances vocales proposées, non confirmées humainement. Un score cosinus n’est pas une probabilité.'}
    except Exception as error:
        from notetaker.infrastructure.process import JobCancelled
        if isinstance(error,JobCancelled): raise
        return {'status':'unavailable','labels':{},'warning':'Identification vocale indisponible ; transcription et brouillon conservés. '+str(error)}
