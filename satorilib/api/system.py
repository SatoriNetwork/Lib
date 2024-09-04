''' the system api is how we talk to the machine, mainly to ask it about system resources '''
import os
import platform
from numpy import mean
import psutil
import time
import shutil
import multiprocessing
import json


def devicePayload(asDict=False):
    ''' returns payload of metrics '''
    total, _, free = getDisk()
    payload = {
        'ram_total_gb': getRam(),
        'ram_available_percent': getRamAvailablePercentage(),
        'cpu': getProcessorCount(),
        'disk_total': total,
        'disk_free': free,
        # 'bandwidth': 'unknown'
    }
    if asDict:
        return payload
    return json.dumps(payload)


def getDisk(path: str = '/Satori/Neuron'):
    '''
    returns ints in gb total, used, free
    since we know this will run in a docker container and probably be mounted
    /Satori/Neuron or /Satori/Neuron/data represents the real disk of the host machine
    '''
    # alt
    # free = (os.statvfs(path).f_bavail * os.statvfs(path).f_frsize) / 1024
    total, used, free = shutil.disk_usage(path)
    return total // (2**30), used // (2**30), free // (2**30)


def getRam():
    ''' returns number of GB of ram on system as int '''
    return round(psutil.virtual_memory().total / (1024.0 ** 3))


def getProcessor():
    ''' name of processor as string '''
    return platform.processor()


def getProcessorCount():
    ''' number of cpus '''
    return multiprocessing.cpu_count()


def getProcessorUsage():
    ''' returns percentage of cpu usage as float '''
    return psutil.cpu_percent()


def getRamDetails():
    ''' returns dictionary containing these keys ['total', 'available', 'percent', 'used', 'free'] '''
    return dict(psutil.virtual_memory()._asdict())

def getSwapDetails():
    ''' returns dictionary containing these keys ['total', 'used', 'free', 'percent', 'sin', 'sout'] '''
    return dict(psutil.swap_memory()._asdict())

def getDiskDetails():
    ''' returns dictionary containing these keys ['total', 'used', 'free', 'percent'] '''
    return dict(psutil.disk_usage('/')._asdict())

def getBootTime():
    ''' returns system boot time as a Unix timestamp '''
    return psutil.boot_time()

def getUptime():
    ''' returns system uptime in seconds '''
    return time.time() - psutil.boot_time()

def getRamAvailablePercentage():
    ''' returns percentage of available ram as float '''
    return psutil.virtual_memory().available * 100 / psutil.virtual_memory().total


def getProcessorUsageOverTime(seconds: int):
    ''' returns average of cpu usage over a number of seconds as float '''
    return mean([psutil.cpu_percent(interval=1) for _ in range(seconds)])


def directorySize(path):
    ''' returns total size of directory in bytes '''
    totalSize = 0
    if not os.path.exists(path):
        return totalSize
    if os.path.isfile(path):
        return os.path.getsize(path)
    if os.path.isdir(path):
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    totalSize += entry.stat().st_size
                elif entry.is_dir():
                    totalSize += directorySize(entry.path)
    return totalSize
