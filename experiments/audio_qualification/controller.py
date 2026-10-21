"""Cancellable, bounded metrics process; models are never loaded."""
import argparse
import os
from .core import ROOT
from experiments.audio_benchmark_20261020.measured import run


def main():
    p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('folder');p.add_argument('--variant',default='exclusive');p.add_argument('--plan');p.add_argument('--baseline-report');p.add_argument('--operator-events');a=p.parse_args()
    from pathlib import Path
    folder=Path(a.folder);folder.mkdir(parents=True,exist_ok=True)
    if (folder/'process').exists() or (folder/'report').exists():raise FileExistsError('Ce calcul existe déjà ; utilisez un nouveau dossier.')
    env={**os.environ,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','PYANNOTE_METRICS_ENABLED':'0'}
    env.pop('HF_TOKEN',None);env.pop('HUGGING_FACE_HUB_TOKEN',None)
    command=[ROOT/'.venv-lab-b/Scripts/python.exe','-m','experiments.audio_qualification.scoring',a.reference,folder/'report','--variant',a.variant]
    if a.plan:command+=['--plan',a.plan]
    if a.baseline_report:command+=['--baseline-report',a.baseline_report]
    if a.operator_events:command+=['--operator-events',a.operator_events]
    measurement=run(command,
        folder/'process',timeout=120,memory_limit=2*1024**3,cancel=folder/'CANCEL',env=env)
    print('Calcul : '+measurement['status'],flush=True)
    return 0 if measurement['status']=='completed' else 2


if __name__=='__main__':raise SystemExit(main())
