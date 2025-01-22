''' an api for reading and writing to disk '''

from typing import Union
import os
import pandas as pd
from satorilib import logging
from satorilib.concepts import StreamId
from satorilib.utils import memory
from satorilib.utils.hash import generatePathId, historyHashes, verifyHashes, cleanHashes, verifyRoot, verifyHashesReturnError
from satorilib.interfaces.model import ModelDataDiskApi
from satorilib.disk.utils import safetify, safetifyWithResult
from satorilib.disk.model import ModelApi
from satorilib.disk.wallet import WalletApi
from satorilib.disk.filetypes.csv import CSVManager


class Disk(ModelDataDiskApi):
    ''' single point of contact for interacting with disk '''

    config = None

    @classmethod
    def setConfig(cls, config):
        cls.config = config
        ModelApi.setConfig(config)
        WalletApi.setConfig(config)

    def __init__(
        self,
        df: pd.DataFrame = None,
        id: StreamId = None,
        loc: str = None,
        ext: str = 'csv',
        **kwargs,
    ):
        self.memory = memory.Memory
        self.csv = CSVManager()
        self.setAttributes(df=df, id=id, loc=loc, ext=ext, **kwargs)

    def setAttributes(
        self,
        df: pd.DataFrame = None,
        id: StreamId = None,
        loc: str = None,
        ext: str = 'csv',
        **kwargs,
    ):
        self.df = df if df is not None else pd.DataFrame()
        self.id = id or StreamId(
            source=kwargs.get('source'),
            author=kwargs.get('author'),
            stream=kwargs.get('stream'),
            target=kwargs.get('target'))
        self.loc = loc
        self.ext = ext
        return self

    def setId(self, id: StreamId = None):
        self.id = id

    ### passthru ###

    @staticmethod
    def defaultModelPath(streamId: StreamId):
        ModelApi.defaultModelPath(streamId)

    @staticmethod
    def saveModel(
        model,
        modelPath: str = None,
        streamId: StreamId = None,
        hyperParameters: list = None,
        chosenFeatures: list = None
    ):
        ModelApi.save(
            model,
            modelPath=modelPath,
            streamId=streamId,
            hyperParameters=hyperParameters,
            chosenFeatures=chosenFeatures)

    @staticmethod
    def loadModel(modelPath: str = None, streamId: StreamId = None):
        return ModelApi.load(modelPath=modelPath, streamId=streamId)

    @staticmethod
    def saveWallet(wallet, walletPath: str = None):
        WalletApi.save(wallet, walletPath=walletPath)

    @staticmethod
    def loadWallet(walletPath: str = None):
        return WalletApi.load(walletPath=walletPath)

    @staticmethod
    def getModelSize(modelPath: str = None):
        return ModelApi.getModelSize(modelPath)

    ### helpers ###

    def safetify(self, path: str):
        path, created = safetifyWithResult(path)
        if created:
            self.saveName()
        return path

    def path(self, filename: str = None):
        '''
        get the path of a file.
        we generate a hash as the id for the datastream so we can store it in a
        folder and avoid worrying about path length limits. also, we can use the
        entire folder as the ipfs hash for the datastream.
        path lengths should about 170 characters long typically. for examples:
        C:\\Users\\user\\AppData\\Local\\Satori\\models\\qZk-NkcGgWq6PiVxeFDCbJzQ2J0=.joblib
        C:\\Users\\user\\AppData\\Local\\Satori\\data\\qZk-NkcGgWq6PiVxeFDCbJzQ2J0=\\aggregate.csv
        C:\\Users\\user\\AppData\\Local\\Satori\\data\\qZk-NkcGgWq6PiVxeFDCbJzQ2J0=\\incrementals\\6c0a15fcfa1c4535ab1da046cc1b5dc8.parquet
        '''
        return (
            self.safetify(
                os.path.join(
                    self.loc or Disk.config.dataPath(),
                    generatePathId(streamId=self.id),
                    filename or f'aggregate.{self.ext}')))

    def exists(self, filename: str = None):
        return os.path.exists(self.path(filename=filename))

    def hashDataFrame(self, df: pd.DataFrame = None, priorRowHash: str = '') -> pd.DataFrame:
        ''' first we have to flattent the columns, then rename them '''
        return historyHashes(
            df=self.csv.conformFlatColumns(self.memory.flatten(df)),
            priorRowHash=priorRowHash)

    def validateAllHashes(self, df: pd.DataFrame = None, priorRowHash: str = '') -> tuple[bool, Union[pd.DataFrame, None]]:
        ''' passthrough for hashing verification '''
        return verifyHashes(df=df if isinstance(df, pd.DataFrame) else self.read(), priorRowHash=priorRowHash)

    def validateAllHashesReturnError(self, df: pd.DataFrame = None, priorRowHash: str = '') -> tuple[bool, Union[pd.DataFrame, None]]:
        ''' passthrough for hashing verification '''
        return verifyHashesReturnError(df=df if isinstance(df, pd.DataFrame) else self.read(), priorRowHash=priorRowHash)

    def cleanByHashes(self, df: pd.DataFrame = None) -> tuple[bool, Union[pd.DataFrame, None]]:
        ''' passthrough for hash cleaning '''
        return cleanHashes(df=df if isinstance(df, pd.DataFrame) else self.read())

    def isARoot(self, df: pd.DataFrame) -> bool:
        ''' checks if the dataframe is a root '''
        return cleanHashes(df)[0]

    def hasRoot(self, df: pd.DataFrame) -> bool:
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return False
        return verifyRoot(df=df if isinstance(df, pd.DataFrame) else self.read())

    def matchesRoot(self, df: pd.DataFrame, localDf: pd.DataFrame = None) -> bool:
        ''' checks if the dataframe is a root '''
        localDf = localDf if localDf is not None else self.read()
        if (
            df is None or
            (isinstance(df, pd.DataFrame) and df.empty) or
            localDf is None or
            (isinstance(localDf, pd.DataFrame) and localDf.empty)
        ):
            return False
        return df.iloc[0].hash == localDf.iloc[0].hash

    ### write ###

    def saveHashes(self, df: pd.DataFrame = None) -> bool:
        ''' saves them all to disk '''
        return self.write(historyHashes(df or self.read()))

    def saveName(self) -> bool:
        ''' writes a readme.md file to disk describing dataset '''
        with open(self.path(filename='readme.md'), mode='w+') as f:
            file_data = f.read()
            if not file_data:
                f.write(self.id.jsonId)
                return True
        return False

    def savePrediction(self, path: str = None, prediction: str = None):
        ''' saves prediction to disk '''
        # todo: we probably should save the predictions to the actual dataset
        #       we can easily parse them out if we use parquet
        #       it's not too much overhead if we use csv
        #       so they should go on the actaul dataset.
        safetify(path)
        with open(path, 'a') as f:
            f.write(prediction)

    def write(self, df: pd.DataFrame) -> bool:
        return self.csv.write(
            filePath=self.path(),
            data=self.updateCache(self.hashDataFrame(df.sort_index())))

    def append(self, df: pd.DataFrame, hashThis: bool = False) -> bool:
        ''' appends to the end of the file while also hashing '''
        if df.shape[0] == 0:
            return False
        # assumes no duplicates...
        df = df.sort_index()
        self.addToCacheCount(df.shape[0])
        if 'hash' in df.columns:
            return self.csv.append(filePath=self.path(), data=df)
        if hashThis:
            df = self.hashDataFrame(
                df=df,
                priorRowHash=self.getHashBefore(df.index[0]))
        else:
            df['hash'] = ''
        return self.csv.append(
            filePath=self.path(),
            data=df)

    def remove(self) -> Union[bool, None]:
        self.csv.remove(filePath=self.path())

    def removeItAndBeforeIt(self, timestamp) -> Union[bool, None]:
        df = self.read()
        self.csv.write(
            filePath=self.path(),
            data=df[df.index > timestamp])

    ### read ###

    def read(self, start: int = None, end: int = None) -> Union[pd.DataFrame, None]:
        if not self.exists():
            return None
        if start == None:
            df = self.csv.read(filePath=self.path())
            self.updateCache(df)
            df = df.sort_index()
            return df
        return self.csv.readLines(filePath=self.path(), start=start, end=end).sort_index()

    def getHashOf(self, time: str) -> Union[str, None]:
        ''' gets the hash of the observation at the given time '''
        before, after, index = self.searchCache(time)
        if index is None:
            return None
        if before == after:
            series = self.read(start=before).iloc[0]
            if series is not None and 'hash' in series:
                return series.hash
            return None
        df = self.read(start=before, end=after)
        if df is not None and 'hash' in df and time in df.index:
            return df.loc[time].hash
        return None

    def getHashBefore(self, time: str, df: pd.DataFrame = None) -> Union[str, None]:
        ''' gets the hash of the observation just before a given time '''
        df = df if df is not None else self.read()
        if df is None or df.shape[0] == 0:
            return ''
        x = df[df.index < time]
        if x.empty:
            return ''
        return x['hash'].values[-1]
    #    def getTheHash(df):
    #
    #        def getRowBeforeTime(df: pd.DataFrame, targetTime: str) -> Union[pd.Series, None]:
    #            timeBeforeTarget = df[df.index < targetTime].index.max()
    #            if timeBeforeTarget is not pd.NaT:
    #                return df.loc[timeBeforeTarget]
    #            return None
    #
    #        if df is not None:
    #            row = getRowBeforeTime(df, time)
    #            if row is not None:
    #                return row.hash
    #        return None
    #
    #    before, after, index = self.searchCache(time)
    #    if index is None:
    #        return None
    #    if before == after:
    #        if (before == 0 or index < time):
    #            series = self.read(start=before).iloc[0]
    #        else:
    #            series = self.read(start=before-1).iloc[0]
    #        if series is not None and 'hash' in series:
    #            return series.hash
    #    else:
    #        theHash = getTheHash(self.read(start=before, end=after))
    #        if theHash is not None:
    #            return theHash
    #    return getTheHash(self.read())

    def getObservationAfter(self, time: str) -> Union[pd.DataFrame, None]:
        ''' gets the observation just after a given time '''

        def getTheRow(df):

            def getRowAfterTime(df: pd.DataFrame, targetTime: str) -> Union[pd.DataFrame, None]:
                timeAfterTarget = df[df.index > targetTime].index.max()
                # not np.nan which is a float
                if timeAfterTarget is not pd.NaT and isinstance(timeAfterTarget, str):
                    return df.loc[[timeAfterTarget]]
                return None

            row = getRowAfterTime(df, time)
            if row is not None:
                return row
            return None

        before, after, index = self.searchCache(time)
        if index is None:
            return None
        if before == after:
            if (before == 0 or index < time):
                df = self.read(start=after, end=after+2)
            else:
                df = self.read(start=after, end=after+2)
            if df is not None:
                return df
        else:
            theRow = getTheRow(self.read(start=before, end=after+2))
            if theRow is not None:
                return theRow
        return getTheRow(self.read())

    def getObservationBefore(self, time: str) -> Union[pd.DataFrame, None]:
        ''' gets the observation just before a given time '''

        def getTheRow(df):

            def getRowBeforeTime(df: pd.DataFrame, targetTime: str) -> Union[pd.DataFrame, None]:
                timeBeforeTarget = df[df.index < targetTime].index.max()
                if timeBeforeTarget is not pd.NaT:
                    return df.loc[[timeBeforeTarget]]
                return None

            row = getRowBeforeTime(df, time)
            if row is not None:
                return row
            return None

        before, after, index = self.searchCache(time)
        if index is None:
            return None
        if before == after:
            if (before == 0 or index < time):
                df = self.read(start=before)
            else:
                df = self.read(start=before-1)
            if df is not None:
                return df
        else:
            theRow = getTheRow(self.read(start=before, end=after))
            if theRow is not None:
                return theRow
        return getTheRow(self.read())

    def gather(
        self,
        targetColumn: 'str|tuple[str]',
        streamIds: list[StreamId] = None,
    ) -> pd.DataFrame:
        ''' retrieves the targets and merges them '''
        streamIds = streamIds or [
            self.id or
            StreamId(
                source=self.df.columns.levels[0],
                author=self.df.columns.levels[1],
                stream=self.df.columns.levels[2],
                target=(
                    self.df.columns.levels[3]
                    if len(self.df.columns.levels) == 4 else None))]
        dfs = []
        for streamId in streamIds:
            df = (self if streamId == self.id else Disk(id=streamId)).read()
            if df is None:
                continue
            dfs.append(self.memory.expand(df=df, streamId=streamId))
        if len(dfs) == 0:
            return None
        if len(dfs) == 1:
            return dfs[0]
        return self.memory.merge(dfs=dfs, targetColumn=targetColumn)
