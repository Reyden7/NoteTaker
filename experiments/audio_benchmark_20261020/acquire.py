"""Pinned official public artifacts; gated Community-1 requires existing access."""
import argparse
import hashlib
import os
import shutil
import urllib.request
import zipfile
from .common import ROOT,OUT,sha,write

ASSETS={
 'large':('Systran/faster-whisper-large-v3','edaa852ec7e145841d8ffdb056a99866b5f0a478','mit',
          ['README.md','config.json','model.bin','preprocessor_config.json','tokenizer.json','vocabulary.json']),
 'moss':('OpenMOSS-Team/MOSS-Transcribe-Diarize','704aa4a9c304e8520be88901e0d1960158ef5b15','apache-2.0',None),
 'alignment':('jonatasgrosman/wav2vec2-large-xlsr-53-french','7c79e105a6525d38e1e69f640b974b4a679723cc','apache-2.0',
              ['README.md','config.json','pytorch_model.bin','preprocessor_config.json','special_tokens_map.json','vocab.json']),
 'community':('pyannote/speaker-diarization-community-1','3533c8cf8e369892e6b79ff1bf80f7b0286a54ee','cc-by-4.0',None)
}
CODE_REV='e3bdd93f8ad58418e04659818efd5fd87a0bc486'


def main():
    p=argparse.ArgumentParser();p.add_argument('asset',choices=[*ASSETS,'moss-code']);a=p.parse_args()
    folder=ROOT/'models/audio-lab'/a.asset;folder.mkdir(parents=True,exist_ok=True)
    if a.asset=='moss-code':
        url=f'https://codeload.github.com/OpenMOSS/MOSS-Transcribe-Diarize/zip/{CODE_REV}'
        archive=folder/'source.zip'
        with urllib.request.urlopen(url,timeout=60) as r,archive.open('wb') as f: shutil.copyfileobj(r,f)
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                if not (folder/member.filename).resolve().is_relative_to(folder.resolve()): raise ValueError('UNSAFE_ARCHIVE')
            z.extractall(folder)
        proof={'repo':'https://github.com/OpenMOSS/MOSS-Transcribe-Diarize','revision':CODE_REV,
               'archive_sha256_computed':sha(archive),'path':str(folder/f'MOSS-Transcribe-Diarize-{CODE_REV}'),
               'license':'Apache-2.0','official':True,'executed':False}
        write(OUT/'assets/moss-code.json',proof);print(proof);return
    os.environ['HF_HUB_DISABLE_XET']='1'
    from huggingface_hub import HfApi,hf_hub_download
    repo,revision,license,selection=ASSETS[a.asset]
    meta=HfApi().model_info(repo,revision=revision,files_metadata=True)
    if meta.sha!=revision or meta.card_data.get('license')!=license: raise ValueError('MODEL_PROVENANCE_MISMATCH')
    files=meta.siblings
    if selection is None: files=[f for f in files if f.rfilename!='.gitattributes' and not f.rfilename.startswith('.eval_results') and not f.rfilename.endswith(('.png','.gif'))]
    else: files=[f for f in files if f.rfilename in selection]
    required=sum(f.size or 0 for f in files if not (folder/f.rfilename).is_file())
    if shutil.disk_usage(ROOT).free<required+5*1024**3: raise OSError('DISK_RESERVE_REQUIRED')
    proof={'repo':repo,'revision':revision,'license':license,'path':str(folder),'files':[],
           'gated':meta.gated,'accepted_conditions_by_agent':False,'production_integrated':False}
    write(OUT/'assets'/(a.asset+'-published.json'),{**proof,'files':[
        {'name':f.rfilename,'size':f.size,'published_lfs_sha256':f.lfs.sha256 if f.lfs else None} for f in files]})
    for f in files:
        print('Acquire '+a.asset+' '+f.rfilename,flush=True)
        path=Path(hf_hub_download(repo,f.rfilename,revision=revision,local_dir=folder))
        actual=sha(path)
        if f.lfs and actual!=f.lfs.sha256: raise ValueError('MODEL_BYTES_MISMATCH')
        if f.size is not None and path.stat().st_size!=f.size: raise ValueError('MODEL_SIZE_MISMATCH')
        proof['files'].append({'name':f.rfilename,'size':path.stat().st_size,'sha256':actual,
                               'published_lfs_sha256':f.lfs.sha256 if f.lfs else None})
    write(OUT/'assets'/(a.asset+'.json'),proof);print('Verified '+a.asset,flush=True)


from pathlib import Path
if __name__=='__main__':main()
