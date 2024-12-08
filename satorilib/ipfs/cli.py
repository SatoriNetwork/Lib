'''
subprocess wrapper for cli communication
'''
import os
import subprocess


class CliCommunicator(object):
    def __init__(self, timeout: int = 0, *args):
        self.shell = []
        if os.name == 'nt':
            self.shell = ['powershell', '-Command']
        self.ipfs = 'ipfs'
        self.timeout = [f'--timeout {timeout}s'] if timeout > 0 else []

    def run(
        self,
        cmd: str = None,
        ipfs: str = None,
        cmds: list[str] = None,
        capture=True,
    ):
        cmds = cmds or cmd.split(' ')
        x = subprocess.run(
            self.shell + [(ipfs or self.ipfs)] + self.timeout + cmds,
            capture_output=capture)
        ret = x.stdout.decode('utf-8').strip()
        if ret == '':
            y = x.stderr.decode('utf-8').strip()
            return y
        return ret
