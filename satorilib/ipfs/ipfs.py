'''
uses the cli to add a file to ipfs

on program start:
# in a separate thread
ipfs.start

on new observation, or publication:
cid = ipfs.addAndPinDirectory(abspath, name)
# send cid to server

on closing a subscription:
cid = ipfs.addAndPinDirectory(abspath, name)
ipfs.removeDirectory(name)
# remvoe cid from server
'''
import os
import json
from typing import Union
from .inps import Ipns
from .cli import CliCommunicator
from satorilib import logging
from satorilib.concepts import StreamId


class Ipfs(CliCommunicator):
    def __init__(self, *args):
        super(Ipfs, self).__init__(*args)
        self.ipns = None
        self.setIpfs()
        self.setVersion()

    def setIpns(self, streamId: StreamId):
        self.ipns = Ipns(streamId)

    def setIpfs(self):
        self.ipfs = self.findOrInstallIpfs()

    def findOrInstallIpfs(self):
        x = self.findIpfs()
        if x is None:
            self.setVersion()
            if self.version == '':
                raise Exception('ipfs not found, and unable to install')
            else:
                x = self.findIpfs()
                if x is None:
                    raise Exception('please install ipfs')
        return x

    def findIpfs(self):
        '''if ipfs is not found in path, look for it in the program directory'''
        for loc in [r'ipfs', r'~\Apps\kubo_v0.17.0\kubo\ipfs.exe']:
            if self.run(ipfs=loc, cmds=['--version']) != '':
                return loc
        return None

    def getVersion(self):
        x = self.run('--version')
        if x == '':
            return None
        return x

    def setVersion(self):
        self.version = self.getVersion() or self.installIpfs()

    def installIpfs(self):
        if os.name == 'nt':
            return self.run(
                r'cd ~;'
                r'wget https://dist.ipfs.tech/kubo/v0.17.0/kubo_v0.17.0_windows-amd64.zip -Outfile kubo_v0.17.0.zip;'
                r'Expand-Archive -Path kubo_v0.17.0.zip -DestinationPath ~\Apps\kubo_v0.17.0;'
                r'cd ~\Apps\kubo_v0.17.0\kubo;'
                r'.\ipfs.exe --version;')
        if os.name == 'posix':
            logging.warning(
                'this should be running in a docker container, and ipfs should already be installed. but we will attempt to install it anyway...')
            return self.run(
                r'wget https://dist.ipfs.tech/kubo/v0.17.0/kubo_v0.17.0_linux-amd64.tar.gz;'
                r'tar -xvzf kubo_v0.17.0_linux-amd64.tar.gz;'
                r'cd kubo && bash install.sh;'
                r'ipfs --version;')
        else:
            logging.warning(
                'unable to install on this platform. install ipfs manually: https://docs.ipfs.tech/install/command-line/#install-official-binary-distributions')

    def addIpfsToPath(self):
        if os.name == 'nt':
            return self.run(
                r'cd ~\Apps\kubo_v0.17.0\kubo;'
                r'$GO_IPFS_LOCATION = pwd;'
                r'if (!(Test-Path -Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force };'
                r'notepad $PROFILE;'
                r'''Add-Content $PROFILE "`n[System.Environment]::SetEnvironmentVariable('PATH',`$Env:PATH+';;$GO_IPFS_LOCATION')";'''
                r'& $profile;'
                r'ipfs --version;')
        elif os.name == 'posix':
            logging.warning('not sure you have to add ipfs to the path')

    def addDirectory(self, abspath: str):
        '''all attempts to use the api for this ended in disaster.'''
        return self.run(f'add -r -Q {abspath}')

    def hashOfDirectory(self, abspath: str):
        '''all attempts to use the api for this ended in disaster.'''
        return self.run(f'add --only-hash -r -Q {abspath}')

    def pinDirectory(self, cid: str, name: str):
        return self.run(f'files cp /ipfs/{cid} /{name}')

    def pinAndAddDirectory(self, abspath: str, name: str):
        return self.run(f'files cp /ipfs/$(ipfs add -r -Q {abspath}) /{name}')

    def init(self):
        return self.run('init')

    def id(self) -> str:
        return self.run('id')

    def addresses(self) -> list[str]:
        try:
            return [x for x in json.loads(self.id())['Addresses'] if isinstance(x, str)]
        except Exception:  # json.JSONDecodeError:
            return []

    def address(self) -> Union[str, None]:
        addressList = [y for y in self.addresses() if (
            '/p2p-circuit/' not in y and
            '/127.0.0.1/' not in y and
            '/udp/' not in y)]
        if len(addressList) > 0:
            return addressList[0]
        return None

    def connect(self, peer: str) -> str:
        return self.run(f'swarm connect {peer}')

    def connectIfMissing(self, peer: str) -> str:
        if peer not in self.peers().split('\n'):
            return self.connect(peer)
        return 'already a peer'

    def peers(self) -> str:
        return self.run('ipfs swarm peers')

    def daemon(self):
        ''' run this in a separate thread '''
        return self.run('daemon')

    def get(self, hash: str, abspath: str = None):
        ''' gets a file from ipfs and saves it to the given path '''
        return self.run(f'get {hash}{f" --output={abspath}" if abspath else ""}')

    ## interface ##################################################################

    def start(self):
        ''' run this in a separate thread '''
        self.init()
        self.daemon()

    def addAndPinDirectory(self, abspath: str, name: str):
        cid = self.addDirectory(abspath)
        self.pinDirectory(cid, name)
        return cid

    def seeMFS(self):
        return self.run('files ls')

    def removeDirectory(self, name: str):
        return self.run(f'files rm -r /{name}')

# QmeikhjXvxT1wzGViPSoE3kgdKpTLKsKm7cLYRBqEQWUKV
# ipfs files ls
# ipfs pin ls
# QmZRAPQF8yG5h3aLeUVGVgDkN9XtiWM9GaHBkehuHWgzs1
# QmXceKTQz8GQx7mepF4BGbhn81tD9u415Z4vnRy9rrFC69
