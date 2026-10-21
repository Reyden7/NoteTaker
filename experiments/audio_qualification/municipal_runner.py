"""CLI coordinator, bounded worker processes, explicit failure and cancellation."""
import argparse
from pathlib import Path
from .municipal import register_source,normalize_audio,run_benchmark,offline_env,write_new
from .core import ROOT,QualificationError


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['import','normalize-worker','run']);p.add_argument('folder',type=Path)
    p.add_argument('--source',type=Path);p.add_argument('--kind',default='real');p.add_argument('--label',default='Conseil municipal');p.add_argument('--device',choices=['cpu','cuda'],default='cuda');a=p.parse_args()
    try:
        if a.action=='normalize-worker':
            from notetaker.infrastructure.offline import enforce_offline,deny_python_network
            enforce_offline();deny_python_network();normalize_audio(a.folder)
        elif a.action=='import':
            if a.source is None:raise QualificationError('Fichier source requis.')
            register_source(a.source,a.folder,a.kind,a.label)
            from experiments.audio_benchmark_20261020.measured import run
            result=run([ROOT/'.venv-lab-a/Scripts/python.exe','-m','experiments.audio_qualification.municipal_runner','normalize-worker',a.folder],
                a.folder/'import-process',timeout=180,memory_limit=2*1024**3,cancel=a.folder/'CANCEL',env=offline_env())
            if result['status']!='completed':raise QualificationError('Import audio en erreur ; original et diagnostic conservés.')
        else:
            project=run_benchmark(a.folder,a.device);print('Projet prêt : '+str(project),flush=True)
        return 0
    except Exception as e:
        print(str(e),flush=True);return 2


if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT/'src'))
    raise SystemExit(main())
