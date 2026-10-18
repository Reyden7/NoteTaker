"""Isolated native feasibility build; active wheels and bundles stay intact."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
import pefile
p=argparse.ArgumentParser()
p.add_argument('--parallel', type=int, default=2)
args=p.parse_args()
source=ROOT/'.cache/ctranslate2-cpu-src'; build=ROOT/'.cache/ctranslate2-cpu-build'
cmake=Path('C:/Program Files (x86)/Microsoft Visual Studio/18/BuildTools/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe')
commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
if commit!='617405f4b050e994e829d527da6caa0e0030afe7': raise ValueError('UNEXPECTED_CPU_SOURCE')
flags=['-DWITH_MKL=OFF','-DWITH_CUDA=OFF','-DWITH_CUDNN=OFF','-DWITH_RUY=ON','-DOPENMP_RUNTIME=NONE',
       '-DBUILD_CLI=OFF','-DBUILD_TESTS=OFF','-DRUY_BUILD_TESTS=OFF','-DRUY_BUILD_BENCHMARKS=OFF',
       '-DCMAKE_POLICY_VERSION_MINIMUM=3.5','-DCMAKE_CXX_FLAGS=/utf-8','-DCMAKE_C_FLAGS=/utf-8']
for label,command in [('configure',[str(cmake),'-S',str(source),'-B',str(build),'-G','Visual Studio 18 2026','-A','x64',*flags]),
                      ('build',[str(cmake),'--build',str(build),'--config','Release','--parallel',str(args.parallel)])]:
    with (ROOT/f'output/quality-02/cpu-runtime-{label}.log').open('wb') as out, (ROOT/f'output/quality-02/cpu-runtime-{label}-stderr.log').open('wb') as err:
        result=subprocess.run(command,stdout=out,stderr=err,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=1800)
    if result.returncode: raise RuntimeError(f'CPU_{label.upper()}_FAILED_{result.returncode}')
dll=build/'Release/ctranslate2.dll'
binary=pefile.PE(str(dll),fast_load=True);binary.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
imports=[e.dll.decode('ascii') for e in binary.DIRECTORY_ENTRY_IMPORT];binary.close()
if any('cudnn' in n.casefold() or 'cuda' in n.casefold() for n in imports): raise ValueError('UNEXPECTED_GPU_CPU_DEPENDENCY')
proof={'status':'compiled_not_inference_qualified','source_commit':commit,'flags':flags,'dll_sha256':sha256_file(dll),
       'dll_size_bytes':dll.stat().st_size,'imports':imports,'inference_tested':False,'application_environment_modified':False,
       'commercial_clearance':False,'submodules':subprocess.check_output(['git','-C',str(source),'submodule','status','--recursive'],text=True).splitlines()}
atomic_json(ROOT/'docs/evidence/ctranslate2-cpu-build.json',proof)
print(json.dumps(proof,ensure_ascii=True,indent=2))
