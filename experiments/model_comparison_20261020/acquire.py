"""Explicit model acquisition for the laboratory, never application startup."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'output/model-comparison/2026-10-20-01'
MODELS = {
    'qwen8': {'repo':'Qwen/Qwen3-8B-GGUF','revision':'7c41481f57cb95916b40956ab2f0b139b296d974',
        'filename':'Qwen3-8B-Q4_K_M.gguf','size':5027783488,
        'sha256':'d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785','license':'apache-2.0'},
    'gemma12': {'repo':'google/gemma-3-12b-it-qat-q4_0-gguf','revision':'7929e34ac7c459bbfd1f38d7358e6839f204578b',
        'filename':'gemma-3-12b-it-q4_0.gguf','size':8074473920,
        'sha256':'dd53172ff3a7b1b16c8fb3d944b87f42a6228ff2de3825b8813ae90d988434cd','license':'gemma'}
}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def save_json(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(path)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('model',choices=list(MODELS))
    parser.add_argument('--local-file',type=Path)
    args=parser.parse_args()
    entry=MODELS[args.model]
    evidence=OUT/'acquisition'/args.model; evidence.mkdir(parents=True,exist_ok=True)
    target=ROOT/'models/experimental-comparison'/args.model/entry['filename']
    # No acceptance or login action. Existing user-configured access may be used.
    os.environ['HF_HUB_DISABLE_XET']='1'
    from huggingface_hub import HfApi, hf_hub_download
    api=HfApi()
    metadata=api.model_info(entry['repo'],revision=entry['revision'],files_metadata=True)
    file=next(s for s in metadata.siblings if s.rfilename==entry['filename'])
    if metadata.sha!=entry['revision'] or metadata.card_data.get('license')!=entry['license'] or file.lfs.sha256!=entry['sha256'] or file.size!=entry['size']:
        raise ValueError('PUBLISHED_PROVENANCE_MISMATCH')
    save_json(evidence/'published-metadata.json',{
        'repo':entry['repo'],'revision':metadata.sha,'license':metadata.card_data.get('license'),
        'gated':metadata.gated,'filename':file.rfilename,'size_bytes':file.size,'published_lfs_sha256':file.lfs.sha256,
        'model_info_api':f"https://huggingface.co/api/models/{entry['repo']}/revision/{entry['revision']}?blobs=true"})
    for filename in ('README.md','LICENSE','NOTICE'):
        if filename not in {s.rfilename for s in metadata.siblings}: continue
        try:
            local=hf_hub_download(entry['repo'],filename,revision=entry['revision'],local_dir=evidence/'upstream')
        except Exception as error:
            save_json(evidence/'access-error.json',{'error_type':type(error).__name__,
                'action':'Obtain the official files using user-approved access; no alternative mirror or gate bypass used.'})
            raise
    if args.local_file:
        local=args.local_file.resolve(strict=True)
        if local.stat().st_size!=entry['size'] or digest(local)!=entry['sha256']: raise ValueError('LOCAL_COPY_NOT_OFFICIAL_BYTES')
        # Use the supplied file in place; copying eight GB is unnecessary.
        target=local
    else:
        if not target.is_file() and shutil.disk_usage(ROOT).free < entry['size']+8*1024**3:
            raise OSError('INSUFFICIENT_DISK_RESERVE')
        target.parent.mkdir(parents=True,exist_ok=True)
        print('Downloading pinned '+entry['repo']+' / '+entry['filename'],flush=True)
        target=Path(hf_hub_download(entry['repo'],entry['filename'],revision=entry['revision'],local_dir=target.parent))
    actual=digest(target)
    if target.stat().st_size!=entry['size'] or actual!=entry['sha256']: raise ValueError('DOWNLOADED_MODEL_INTEGRITY_FAILED')
    proof={**entry,'path':str(target),'actual_sha256':actual,'verified':True,
        'official_publisher':True,'production_integrated':False,'license_acceptance_performed_by_agent':False}
    save_json(evidence/'verified.json',proof)
    print(json.dumps(proof,ensure_ascii=True),flush=True)


if __name__=='__main__': main()
