# mainly used for generating unique ids for data and model paths since they must be short

from typing import Union
import base64
import hashlib
import pandas as pd
# from satorilib.concepts import StreamId # recursive import


def generatePathId(path: str = None, streamId: 'StreamId' = None):
    hasher = hashlib.sha1((path or streamId.idString).encode('utf-8'))
    removals = r'\/:*?"<>|=-'
    ret = base64.urlsafe_b64encode(hasher.digest())
    ret = ret.decode("utf-8")
    for char in removals:
        if char in ret:
            ret = ret.replace(char, '-')
    return ret


def hashRow(priorRowHash: str, ts: str, value: str) -> str:
    return hashIt(priorRowHash + ts + value)


def hashIt(string: str) -> str:
    # return hashlib.sha256(rowStr.encode()).hexdigest() # 74mb
    # return hashlib.md5(rowStr.encode()).hexdigest() # 42mb
    return hashlib.blake2s(
        string.encode(),
        digest_size=8).hexdigest()  # 27mb / million rows


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


def verifyRoot(df: pd.DataFrame) -> bool:
    ''' returns true if root hash is empty string plus the first row '''
    for index, row in df.iterrows():
        rowStr = '' + str(index) + str(row['value'])
        rowHash = hashIt(rowStr)
        if rowHash == row['hash']:
            return True
        return False
    return False


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
    priorRow = None
    for index, row in df.iterrows():
        rowHash = hashIt(priorRowHash + str(index) + str(row['value']))
        if rowHash != row['hash']:
            return False, priorRow.to_frame().T if isinstance(priorRow, pd.Series) else None
        priorRowHash = rowHash
        priorRow = row
    return True, None


def verifyHashesReturnError(df: pd.DataFrame, priorRowHash: str = None) -> tuple[bool, Union[pd.DataFrame, None]]:
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
        rowHash = hashIt(priorRowHash + str(index) + str(row['value']))
        if rowHash != row['hash']:
            return False, row.to_frame().T
        priorRowHash = rowHash
    return True, None

# verifyHashes(pd.DataFrame({'value':[1,2,3,4,5,6], 'hash':['ce8efc6eeb9fc30b','e2cc1a4e70bdba14','42359a663f6c3e30','6278827c73894e0c','c7a6682880ee6f8d','d607268c4f2e75ed']}, index=[0,1,2,3,4,9,5]))


def verifyHashesReturnLastGood(df: pd.DataFrame, priorRowHash: str = None) -> tuple[bool, Union[pd.DataFrame, None]]:
    ''' returns success flag and the last known good row as DataFrame '''
    if df.empty:
        return True, None
    priorRowHash = priorRowHash or ''
    for index, row in df.iterrows():
        rowHash = hashIt(priorRowHash + str(index) + str(row['value']))
        if rowHash != row['hash']:
            return False, priorRow.to_frame().T
        priorRowHash = rowHash
        priorRow = row
    return True, row


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

# cleanHashes(pd.DataFrame({'value':[1,2,3,4,5,6], 'hash':['ce8efc6eeb9fc30b','e2cc1a4e70bdba14','42359a663f6c3e30','6278827c73894e0c','c7a6682880ee6f8d','d607268c4f2e75ed']}, index=[0,1,2,3,4,9,5]))
# cleanHashes(pd.DataFrame({'value':[1,2,3,4,5,9,6], 'hash':['ce8efc6eeb9fc30b','e2cc1a4e70bdba14','42359a663f6c3e30','6278827c73894e0c','c7a6682880ee6f8d','erroneous row','d607268c4f2e75ed']}, index=[0,1,2,3,4,9,5]))

class PasswordHash():

    @staticmethod
    def hash(
        password:str,
        salt: Union[str, None]= None,
        iterations: int = 100000
    ) -> bytes:
        import hashlib
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            (salt or f'{password}sha256').encode(),
            iterations)

    @staticmethod
    def toString(hash:bytes) -> str:
        return hash.hex()

    @staticmethod
    def verify(password:Union[bytes,str], target:Union[bytes,str]) -> bool:
        return target == password

    @staticmethod
    def generateTarget(password: str) -> bool:
        return PasswordHash.toString(
            PasswordHash.hash(
                PasswordHash.toString(
                    PasswordHash.hash(password))))


'''dart version
import 'dart:convert';
import 'package:crypto/crypto.dart';

class PasswordHash {
  static List<int> hash(
    String password, {
    String? salt,
    int iterations = 100000,
  }) {
    final usedSalt = salt ?? '${password}sha256';
    final pbkdf2 = Pbkdf2(
      macAlgorithm: Hmac.sha256(),
      iterations: iterations,
      bits: 256,
    );

    return pbkdf2.deriveKey(
      secretKey: SecretKey(utf8.encode(password)),
      nonce: utf8.encode(usedSalt),
    );
  }

  static String toString(List<int> hashBytes) {
    return hex.encode(hashBytes);
  }

  static bool verify(dynamic password, dynamic target) {
    return target == password;
  }

  static String generateTarget(String password) {
    final firstHash = hash(password);
    final firstHashString = toString(firstHash);
    final secondHash = hash(firstHashString);
    return toString(secondHash);
  }
}
'''
