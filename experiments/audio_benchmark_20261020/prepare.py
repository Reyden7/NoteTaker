"""Read-only source discovery; exact PCM crops and preserved annotations."""
import shutil
import wave
from .common import ROOT,OUT,read,sha,new


def main():
    previous=ROOT/'output/diagnostic-parcoursup/2026-10-20-01'
    manifest=read(previous/'manifest.json')
    audio=Path(manifest['source_audio'])
    if sha(audio)!=manifest['audio_sha256']: raise ValueError('SOURCE_AUDIO_CHANGED')
    source_files=list((ROOT/'src').rglob('*.py'))
    source_files += [ROOT/'models_manifest.json',ROOT/'diarization_models_manifest.json',
        previous/'comparaison-v2/correction-humaine-originale.txt',previous/'reference-humaine-originale.txt',
        ROOT/'output/direct-summary/reference-humaine/annotations.json']
    pack={'source_audio':str(audio),'source_audio_sha256':sha(audio),
        'protected':{str(p):sha(p) for p in source_files},'cases':{},'human_audio_review_by_agent':False}
    with wave.open(str(audio),'rb') as stream:
        assert (stream.getframerate(),stream.getnchannels(),stream.getsampwidth())==(16000,1,2)
        for label,start,frames in [('60s',1080,60*16000),('180s',1051.960,180*16000),('full',0,stream.getnframes())]:
            target=OUT/'audio'/(label+'.wav'); target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists(): raise FileExistsError(target)
            stream.setpos(round(start*16000)); pcm=stream.readframes(frames)
            with wave.open(str(target),'wb') as dst:
                dst.setparams(stream.getparams()); dst.writeframes(pcm)
            pack['cases'][label]={'audio':str(target),'start_in_original_seconds':start,
                'duration_seconds':len(pcm)/32000,'sha256':sha(target),'pcm_exact_copy':True}
    old=read(ROOT/'output/direct-summary/reference-humaine/annotations.json')
    pack['annotation_inventory']={'excerpts':len(old['excerpts']),
        'human_checked':sum(bool(x.get('human_checked')) for x in old['excerpts']),
        'global_human_reference_completed':old.get('human_reference_completed',False),
        'verbatim_gold_available':False,'rttm_gold_available':False}
    copies=OUT/'references';copies.mkdir(parents=True,exist_ok=True)
    for name,path in [('correction-humaine.txt',previous/'comparaison-v2/correction-humaine-originale.txt'),
                      ('reference-narrative.txt',previous/'reference-humaine-originale.txt'),
                      ('annotations-12-extraits-originales.json',ROOT/'output/direct-summary/reference-humaine/annotations.json')]:
        if (copies/name).exists(): raise FileExistsError(copies/name)
        shutil.copyfile(path,copies/name)
    new(OUT/'manifest.json',pack)
    print(pack['annotation_inventory']);print(pack['cases'])


from pathlib import Path
if __name__=='__main__': main()
