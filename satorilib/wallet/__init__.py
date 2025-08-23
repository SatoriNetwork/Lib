from satorilib.wallet.wallet import Wallet
from satorilib.wallet.evrmore import scripts
from satorilib.wallet.evrmore import EvrmoreWallet
from satorilib.wallet.ethereum.wallet import EthereumWallet
from satorilib.wallet.ravencoin import RavencoinWallet
from satorilib.wallet.utils.transaction import TxUtils
from satorilib.wallet.utils.validate import Validate

__all__ = [
    "Wallet",
    "EvrmoreWallet",
    "EthereumWallet",
    "RavencoinWallet",
    "TxUtils",
    "Validate",
    "scripts",
]

# not needed yet, just an example of return data from electrumx servers
# def parseTx(txStruct):
#    ''' example:
#    {
#        "blockhash": "0000000000000000015a4f37ece911e5e3549f988e855548ce7494a0a08b2ad6",
#        "blocktime": 1520074861,
#        "confirmations": 679,
#        "hash": "36a3692a41a8ac60b73f7f41ee23f5c917413e5b2fad9e44b34865bd0d601a3d",
#        "hex": "01000000015bb9142c960a838329694d3fe9ba08c2a6421c5158d8f7044cb7c48006c1b484000000006a4730440220229ea5359a63c2b83a713fcc20d8c41b20d48fe639a639d2a8246a137f29d0fc02201de12de9c056912a4e581a62d12fb5f43ee6c08ed0238c32a1ee769213ca8b8b412103bcf9a004f1f7a9a8d8acce7b51c983233d107329ff7c4fb53e44c855dbe1f6a4feffffff02c6b68200000000001976a9141041fb024bd7a1338ef1959026bbba860064fe5f88ac50a8cf00000000001976a91445dac110239a7a3814535c15858b939211f8529888ac61ee0700",
#        "locktime": 519777,
#        "size": 225,
#        "time": 1520074861,
#        "txid": "36a3692a41a8ac60b73f7f41ee23f5c917413e5b2fad9e44b34865bd0d601a3d",
#        "version": 1,
#        "vin": [ {
#            "scriptSig": {
#            "asm": "30440220229ea5359a63c2b83a713fcc20d8c41b20d48fe639a639d2a8246a137f29d0fc02201de12de9c056912a4e581a62d12fb5f43ee6c08ed0238c32a1ee769213ca8b8b[ALL|FORKID] 03bcf9a004f1f7a9a8d8acce7b51c983233d107329ff7c4fb53e44c855dbe1f6a4",
#            "hex": "4730440220229ea5359a63c2b83a713fcc20d8c41b20d48fe639a639d2a8246a137f29d0fc02201de12de9c056912a4e581a62d12fb5f43ee6c08ed0238c32a1ee769213ca8b8b412103bcf9a004f1f7a9a8d8acce7b51c983233d107329ff7c4fb53e44c855dbe1f6a4"
#            },
#            "sequence": 4294967294,
#            "txid": "84b4c10680c4b74c04f7d858511c42a6c208bae93f4d692983830a962c14b95b",
#            "vout": 0}],
#        "vout": [ { "n": 0,
#            "scriptPubKey": {
#                "addresses": ["12UxrUZ6tyTLoR1rT1N4nuCgS9DDURTJgP"],
#                "asm": "OP_DUP OP_HASH160 1041fb024bd7a1338ef1959026bbba860064fe5f OP_EQUALVERIFY OP_CHECKSIG",
#                "hex": "76a9141041fb024bd7a1338ef1959026bbba860064fe5f88ac",
#                "reqSigs": 1,
#                "type": "pubkeyhash"},
#            "value": 0.0856647},
#            { "n": 1,
#            "scriptPubKey": {
#                "addresses": [ "17NMgYPrguizvpJmB1Sz62ZHeeFydBYbZJ"],
#                "asm": "OP_DUP OP_HASH160 45dac110239a7a3814535c15858b939211f85298 OP_EQUALVERIFY OP_CHECKSIG",
#                "hex": "76a91445dac110239a7a3814535c15858b939211f8529888ac",
#                "reqSigs": 1,
#                "type": "pubkeyhash"},
#            "value": 0.1360904},
#            { "n":2,
#            "scriptPubKey":{
#                "asm":"OP_DUP OP_HASH160 77c5fa192c69c7341f8b6759c5762493c27886be OP_EQUALVERIFY OP_CHECKSIG OP_RVN_ASSET 1772766e740a504f524b5950554e582100e1f5050000000075",
#                "hex":"76a91477c5fa192c69c7341f8b6759c5762493c27886be88acc01772766e740a504f524b5950554e582100e1f5050000000075",
#                "reqSigs":1,
#                "type":"transfer_asset",
#                "asset":{
#                    "name":"PORKYPUNX!",
#                    "amount":1},
#                "addresses":["RLCVf2Jb7oPHwAdmzrhpSoQygbKz82Xbs1"]},
#            "value":0,
#            "valueSat":0},
#            { "n":3,
#            "scriptPubKey":{
#                "asm":"OP_DUP OP_HASH160 f7addfa2061fb7752a81b7fbb1de409b62efcb63 OP_EQUALVERIFY OP_CHECKSIG OP_RVN_ASSET 1872766e6f13504f524b5950554e582f41495244524f50322175",
#                "hex":"76a914f7addfa2061fb7752a81b7fbb1de409b62efcb6388acc01872766e6f13504f524b5950554e582f41495244524f50322175",
#                "reqSigs":1,
#                "type":"new_asset",
#                "asset":{
#                    "name":"PORKYPUNX\/AIRDROP2!",
#                    "amount":1},
#                "addresses":["RXroGqyy9yq7kEKztP4RZWgQrXzmUzMxAL"]},
#            "value":0,
#            "valueSat":0}]}
#    '''
