import pandas as pd
import hashlib
import base64
from typing import Union
from satorilib.disk import Cache
from satorilib.concepts import StreamId
from satorineuron import config
Cache.setConfig(config)
streams = [
    {"source": "satori", "author": "021bd7999774a59b6d0e40d650c2ed24a49a54bdb0b46c922fd13afe8a4f3e4aeb",
        "stream": "coinbaseADA-USD", "target": "data.rates.ADA"},
    {"source": "satori", "author": "0355efd5fbc8ee719669d775026018a9097120bb2707b0ae1d92e0371907c754f6",
        "stream": "coinbaseDOGE-USD", "target": "data.rates.DOGE"},
    {"source": "satori", "author": "03a577ef176bc7a82be4f1d50966c8f18932c795660eb6d482e36363e98d472ea5",
        "stream": "coinbaseETH-USD", "target": "data.rates.ETH"},
    {"source": "satori", "author": "021bd7999774a59b6d0e40d650c2ed24a49a54bdb0b46c922fd13afe8a4f3e4aeb",
        "stream": "coinbaseALGO-USD", "target": "data.rates.ALGO"},
    {"source": "satori", "author": "0355efd5fbc8ee719669d775026018a9097120bb2707b0ae1d92e0371907c754f6",
        "stream": "coinbaseAVAX-USD", "target": "data.rates.AVAX"},
    {"source": "satori", "author": "03a577ef176bc7a82be4f1d50966c8f18932c795660eb6d482e36363e98d472ea5",
        "stream": "coinbaseBTC-USD", "target": "data.rates.BTC"},
    {"source": "satori", "author": "0355efd5fbc8ee719669d775026018a9097120bb2707b0ae1d92e0371907c754f6",
        "stream": "coinbaseHBAR-USD", "target": "data.rates.HBAR"},
]
stream = {"source": "satori", "author": "021bd7999774a59b6d0e40d650c2ed24a49a54bdb0b46c922fd13afe8a4f3e4aeb",
          "stream": "coinbaseADA-USD", "target": "data.rates.ADA"}
s = StreamId.fromMap(stream)
disk = Cache(id=s)
df = disk.read()
disk.write(disk.hashDataFrame(df))

for stream in streams:
    disk = Cache(id=StreamId.fromMap(stream))
    disk.write(disk.hashDataFrame(disk.read()))

time = '2023-10-12 20:02:50.637233'
disk.getObservationAfter(time)


def hashIt(string: str) -> str:
    # return hashlib.sha256(rowStr.encode()).hexdigest() # 74mb
    # return hashlib.md5(rowStr.encode()).hexdigest() # 42mb
    return hashlib.blake2s(
        string.encode(),
        digest_size=8).hexdigest()  # 27mb / million rows


def cleanHashes(df: pd.DataFrame) -> tuple[bool, Union[pd.DataFrame, None]]:
    '''
    returns success flag and the cleaned DataFrame or None
    success is true if the first hash is the first value plus ''.
    if it is able to create a dataframe of all the other hashes from there and
    that dataframe is different than the input dataframe, it returns it. if it's
    unable to make a new dataframe or the one it makes matches the input, it
    returns None.
    '''
    priorRowHash = ''
    i = 0
    success = False
    rows = []
    for index, row in df.iterrows():
        rowStr = priorRowHash + str(index) + str(row['value'])
        rowHash = hashIt(rowStr)
        if i == 0 and row['hash'] == rowHash:
            success = True
        i += 1
        if rowHash != row['hash']:
            # skip this row
            continue
        rows.append(row)
        priorRowHash = rowHash
    dfReturn = pd.DataFrame(rows, columns=df.columns)
    if dfReturn.equals(df):
        return success, None
    return success, dfReturn


def verifyHashes(df: pd.DataFrame, priorRowHash: str = None) -> tuple[bool, Union[pd.DataFrame, None]]:
    '''
    returns success flag and the first row as DataFrame that doesn't pass the
    hash check or None
    priorRowHash isn't usually passed in because we do the verification on the
    entire dataframe, so by default the first priorRowHash is assumed to be an
    empty string because it's the first peice of data that was recorded. if new
    data was found before it, all the hashes change.
    '''
    priorRowHash = priorRowHash or ''
    for index, row in df.iterrows():
        rowStr = priorRowHash + str(index) + str(row['value'])
        rowHash = hashIt(rowStr)
        if rowHash != row['hash']:
            return False, row.to_frame().T
        priorRowHash = rowHash
    return True, None


hashIt('2023-10-12 20:02:50.6372330.24345')
hashIt('f4791015256a8fb42023-12-10 19:12:31.6579480.59690')  # 510fde0b073c712c


def historyHashes(df: pd.DataFrame, priorRowHash: str = None) -> pd.DataFrame:
    ''' creates hashes of every row in the dataframe based on prior hash '''
    priorRowHash = priorRowHash or ''
    rowHashes = []
    for index, row in df.iterrows():
        rowStr = priorRowHash + str(index) + str(row['value'])
        rowHash = hashIt(rowStr)
        rowHashes.append(rowHash)
        priorRowHash = rowHash
    df['hash'] = rowHashes
    return df


targetTime = '2023-10-12 20:03:50.637235'
# 2023-12-15 05:42:43.422315,0.6336,5eaf8c71d19629c8
