'''
ipns methods
see https://docs.ipfs.tech/concepts/ipns/#example-ipns-setup-with-cli
https://docs.ipfs.tech/how-to/publish-ipns/#publishing-ipns-names-with-kubo
not finished.
'''
from satorilib.concepts import StreamId
from satorilib.ipfs.cli import CliCommunicator


class Ipns(CliCommunicator):
    def __init__(self, streamId: StreamId, *args):
        super(Ipns, self).__init__(*args)
        self.key = ''
        self.id = streamId or StreamId.empty()

    @property
    def name(self):
        return self.id.jsonId

    def associateKeyWithStream(self):
        '''saves locally tells server'''
        self.key = self.generateKey()
        self.tellServer()

    def generateKey(self):
        return self.run(f'ipfs key gen {self.name}')
        # return os.popen(f'ipfs key gen {self.name}').read()
        # return subprocess.Popen(
        #    f'ipfs key gen {streamName}',
        #    shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,)

    def tellServer(self):
        '''endpoint'''

    def getKeyOf(self):
        return self.run(f'curl https://gateway.ipfs.io/ipns/{self.key}')

    def get(self):
        return self.run(f'curl https://gateway.ipfs.io/ipns/{self.key}')

    def publish(self, ipfs):
        return self.run(f'ipfs name publish --key={self.name} /ipfs/{ipfs}')

    def getMostPopular(self, ipnsKeys):
        '''
        do we want to get most popluar (a heuristic)
        or do we want to see which one has the longest data?
        more true, but more work. do this first.'''
        x = {key:
             f'ipfs name resolve --key={key}'
             for key in ipnsKeys}
        return max(set(x.values), key=x.values.count)

    def randomlyChooseKeyFromMostPopular(self, ipnsKeys):
        '''get a key'''
        import random
        x = self.getMostPopular(ipnsKeys)
        candidates = {key: value for key,
                      value in ipnsKeys.items() if value == x}
        return random.choice(list(candidates.keys()))
