from satorilib.disk.wallet import WalletApi
from satorilib import secret
from satorineuron import config
from satorilib.wallet import EvrmoreWallet
from satorilib.disk import Cache  # Disk
Cache.setConfig(config)
self = EvrmoreWallet('/Satori/Neuron/wallet/wallet.yaml')
content = {
    'entropy': self._entropyStr,
    'words': self.words,
    'privateKey': self.privateKey,
}
en = secret.encryptMapValues(
    content=content,
    password='password',
    keys=['entropy', 'privateKey', 'words'])
WalletApi.save(
    walletPath='/Satori/Neuron/wallet/vault-name.yaml',
    wallet={
        **(self.yaml if hasattr(self, 'yaml') and isinstance(self.yaml, dict) else {}),
        **en,
        **{
            'publicKey': self.publicKey,
            'scripthash': self.scripthash,
            self.symbol: {'address': self.address}}})
