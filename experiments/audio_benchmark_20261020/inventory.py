"""Record installed logical footprint and licenses without reading credentials."""
import argparse
import importlib.metadata as metadata
import platform
import sys
from pathlib import Path
import psutil
from .common import ROOT,OUT,sha,write


def main():
    parser=argparse.ArgumentParser();parser.add_argument('name');args=parser.parse_args()
    packages=[]
    for dist in metadata.distributions():
        files=[];size=shared=0
        for f in dist.files or []:
            p=Path(dist.locate_file(f))
            if not p.is_file():continue
            stat=p.stat();size+=stat.st_size
            if stat.st_nlink>1:shared+=stat.st_size
            if 'license' in p.name.lower() or p.name.upper() in {'COPYING','NOTICE'}:files.append(str(p))
        packages.append({'name':dist.metadata['Name'],'version':dist.version,'logical_bytes':size,
            'bytes_in_files_with_multiple_hardlinks':shared,
            'license_expression':dist.metadata.get('License-Expression'),
            'license_field':dist.metadata.get('License'),
            'license_files':files,'classifiers':[v for v in dist.metadata.get_all('Classifier',[]) if v.startswith('License')]})
    snapshot={'environment':args.name,'interpreter':sys.executable,'python':platform.python_version(),
        'isolated_prefix':sys.prefix,'packages':packages,'logical_dependency_bytes':sum(p['logical_bytes'] for p in packages),
        'size_scope':'Installed logical package bytes. uv hardlinks can share disk blocks with its cache; not all bytes are physically duplicated.',
        'host':{'platform':platform.platform(),'cpu_logical':psutil.cpu_count(),'cpu_physical':psutil.cpu_count(logical=False),
                'ram_total_bytes':psutil.virtual_memory().total,'ram_available_bytes':psutil.virtual_memory().available,
                'disk_free_bytes':psutil.disk_usage(str(ROOT)).free}}
    write(OUT/'environments'/(args.name+'.json'),snapshot)
    write(OUT/'environments'/(args.name+'-freeze.txt'),'\n'.join(sorted(p['name']+'=='+p['version'] for p in packages)))
    print(args.name,platform.python_version(),snapshot['logical_dependency_bytes'])


if __name__=='__main__':main()
