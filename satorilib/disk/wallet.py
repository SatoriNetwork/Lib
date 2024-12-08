
import os
from satorilib.interfaces.wallet import WalletDiskApi
from satorilib.disk.utils import safetify


class WalletApi(WalletDiskApi):

    config = None

    @classmethod
    def setConfig(cls, config):
        cls.config = config

    @staticmethod
    def save(wallet, walletPath: str = None):
        walletPath = walletPath or WalletApi.config.walletPath()
        safetify(walletPath)
        WalletApi.config.put(data=wallet, path=walletPath)

    @staticmethod
    def load(walletPath: str = None):
        walletPath = walletPath or WalletApi.config.walletPath()
        if os.path.exists(walletPath):
            return WalletApi.config.get(walletPath)
        return False
