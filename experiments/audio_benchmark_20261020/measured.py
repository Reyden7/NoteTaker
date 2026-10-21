"""Owned Windows job: enforce committed-memory ceiling before resuming child."""
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes as w
from pathlib import Path
import psutil
from .common import ROOT,write

sys.path.insert(0,str(ROOT/'src'))
from notetaker.infrastructure.windows_job import WindowsJob
from notetaker.infrastructure.cpu_profile import job_cpu


class Basic(ctypes.Structure):
    _fields_=[('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),('flags',w.DWORD),
        ('min_working_set',ctypes.c_size_t),('max_working_set',ctypes.c_size_t),('active_processes',w.DWORD),
        ('affinity',ctypes.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
class IO(ctypes.Structure):
    _fields_=[(key,ctypes.c_ulonglong) for key in ('read_count','write_count','other_count','read_bytes','write_bytes','other_bytes')]
class Extended(ctypes.Structure):
    _fields_=[('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),
              ('peak_process_memory',ctypes.c_size_t),('peak_job_memory',ctypes.c_size_t)]


def run(command,folder,*,timeout=900,memory_limit=12*1024**3,cancel=None,env=None):
    if os.name!='nt': raise OSError('WINDOWS_JOB_REQUIRED')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter(); process=job=None
    samples=[]; peak_rss=peak_windows_wset=0; reason=None
    record={'command':[str(x) for x in command],'memory_limit_bytes':memory_limit,
            'memory_limit_kind':'Windows job aggregate committed memory, enforced before child resume',
            'status':'starting','sample_interval_seconds':0.25}
    write(folder/'measurement.json',record)
    with (folder/'stdout.txt').open('wb') as stdout,(folder/'stderr.txt').open('wb') as stderr:
        try:
            process=subprocess.Popen([str(x) for x in command],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,
                stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW|0x4)
            job=WindowsJob(process)
            info=Extended(); info.basic.flags=0x2000|0x100|0x200
            info.process_memory=info.job_memory=memory_limit
            if not job.api.SetInformationJobObject(job.handle,9,ctypes.byref(info),ctypes.sizeof(info)):
                raise ctypes.WinError(ctypes.get_last_error())
            root=psutil.Process(process.pid)
            root.resume()
            record.update(status='running',pid=process.pid)
            write(folder/'measurement.json',record)
            pressure_since=None
            while process.poll() is None:
                elapsed=time.perf_counter()-started
                if cancel is not None and Path(cancel).exists(): reason='cancelled';break
                if elapsed>timeout: reason='timeout';break
                rss=0
                try: descendants=root.children(recursive=True)
                except psutil.NoSuchProcess: break
                for p in [root,*descendants]:
                    try:
                        mem=p.memory_info();rss+=mem.rss
                        peak_windows_wset=max(peak_windows_wset,getattr(mem,'peak_wset',mem.rss))
                    except (psutil.NoSuchProcess,psutil.AccessDenied): pass
                peak_rss=max(peak_rss,rss)
                available=psutil.virtual_memory().available
                samples.append({'elapsed':elapsed,'tree_rss':rss,'system_available':available})
                if available<1024**3:
                    pressure_since=pressure_since or elapsed
                    if elapsed-pressure_since>3: reason='system_memory_pressure';break
                else: pressure_since=None
                time.sleep(0.25)
            if reason:
                # Closing this owned handle kills its descendants, not unrelated workers.
                record['cpu']=job_cpu(job)
                final=Extended()
                job.api.QueryInformationJobObject(job.handle,9,ctypes.byref(final),ctypes.sizeof(final),None)
                record['peak_job_committed_bytes']=final.peak_job_memory
                record['configured_job_memory_limit_bytes']=final.job_memory
                job.close();process.wait(timeout=10)
            else:
                process.wait()
                record['cpu']=job_cpu(job)
                final=Extended()
                if not job.api.QueryInformationJobObject(job.handle,9,ctypes.byref(final),ctypes.sizeof(final),None):
                    raise ctypes.WinError(ctypes.get_last_error())
                record['peak_job_committed_bytes']=final.peak_job_memory
                record['configured_job_memory_limit_bytes']=final.job_memory
            record.update(status=reason or ('completed' if process.returncode==0 else 'failed'),
                exit_code=process.returncode)
        except BaseException as error:
            record.update(status='controller_error',error_type=type(error).__name__,error=str(error))
            raise
        finally:
            if job: job.close()
            if process and process.poll() is None: process.kill();process.wait()
            record.update(wall_seconds=time.perf_counter()-started,peak_sampled_tree_rss_bytes=peak_rss,
                peak_observed_windows_process_working_set_bytes=peak_windows_wset,
                working_set_measurement='Windows peak counter observed during sampling; job committed peak is retained by the kernel.',
                sample_count=len(samples))
            write(folder/'samples.json',samples);write(folder/'measurement.json',record)
    return record
