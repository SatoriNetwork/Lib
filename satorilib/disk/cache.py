''' an api for reading and writing to disk '''

from typing import Union
import os
import pandas as pd
from satorilib import logging
from satorilib.concepts import StreamId
from satorilib.utils import memory
from satorilib.utils.time import datetimeToTimestamp, earliestDate, now
from satorilib.utils.hash import hashIt, generatePathId, historyHashes, verifyHashes, cleanHashes, verifyRoot, verifyHashesReturnError, verifyHashesReturnLastGood
from satorilib.disk import Disk
from satorilib.disk.utils import safetify, safetifyWithResult
from satorilib.disk.model import ModelApi
from satorilib.disk.wallet import WalletApi
from satorilib.disk.filetypes.csv import CSVManager
from satorilib.concepts import Observation


class CachedResult():
    def __init__(
        self,
        time: str,
        data: str,
        hash: str,
        success: bool,
        validated: Union[bool, None] = None,
        validatedFrame: Union[pd.DataFrame, None] = None,
    ):
        self.time = time
        self.data = data
        self.hash = hash
        self.success = success
        self.validated = validated
        self.validatedFrame = validatedFrame


class Cache(Disk):
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
        super().__init__(df=df, id=id, loc=loc, ext=ext, **kwargs)
        self.loadCache()
        self.checkedHash = ''
        self.checkedIndex = None

    def __str__(self):
        return f'Cache({self.id}, {self.df.tail()})'

    ### passthru ###

    def clearCache(self):
        self.df = pd.DataFrame()

    def updateCacheSimple(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None:
            return self.df
        self.df = df
        return self.df

    def updateCache(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None:
            return self.df
        name = df.index.name or 'index'
        self.df = (
            df
            .reset_index()
            .drop_duplicates(subset=[name], keep='last')
            .set_index(name)
            .sort_index())
        return self.df

    def updateCacheShowDifference(self, df: pd.DataFrame) -> pd.DataFrame:
        def safeFloatConvert(x):
            try:
                return float(x)
            except ValueError:
                return x

        prior = self.df.copy()
        if df is not None:
            self.updateCache(df)
        name = self.df.index.name or 'index'
        dfIndexed = self.df.reset_index()
        priorIndexed = prior.reset_index()
        common = dfIndexed.columns.intersection(priorIndexed.columns).tolist()
        try:
            dfIndexed['value'] = dfIndexed['value'].apply(safeFloatConvert)
            priorIndexed['value'] = priorIndexed['value'].apply(
                safeFloatConvert)
            merged = pd.merge(
                dfIndexed,
                priorIndexed,
                how='outer',
                on=common,
                validate=None,
                indicator=True)
        except Exception as e:
            logging.error('merge error', e, color='red')
        differences = (
            merged[merged['_merge'] != 'both']
            .drop(columns=['_merge'])
            .set_index(name))
        return differences

    def search(
        self,
        time: str,
        before: bool = False,
        after: bool = False,
        exact: bool = False
    ) -> pd.DataFrame:
        if (
            not isinstance(time, str) or
            not any([before, after, exact]) or
            self.df is None
        ):
            return None
        if before:
            return self.df[self.df.index < time]
        if after:
            return self.df[self.df.index > time]
        if exact:
            return self.df[self.df.index == time]
        return None

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
                    self.loc or Cache.config.dataPath(),
                    generatePathId(streamId=self.id),
                    filename or f'aggregate.{self.ext}')))

    def exists(self, filename: str = None):
        return os.path.exists(self.path(filename=filename))

    def hashDataFrame(self, df: pd.DataFrame = None, priorRowHash: str = '') -> pd.DataFrame:
        ''' first we have to flattent the columns, then rename them '''
        return historyHashes(
            df=self.csv.conformFlatColumns(self.memory.flatten(
                df if isinstance(df, pd.DataFrame) else self.df)),
            priorRowHash=priorRowHash)

    def validateAllHashes(self, df: pd.DataFrame = None, priorRowHash: str = '') -> tuple[bool, Union[pd.DataFrame, None]]:
        ''' passthrough for hashing verification '''
        return verifyHashes(df=df if isinstance(df, pd.DataFrame) else self.df, priorRowHash=priorRowHash)

    def validateAllHashesReturnError(self, df: pd.DataFrame = None, priorRowHash: str = '') -> tuple[bool, Union[pd.DataFrame, None]]:
        ''' passthrough for hashing verification '''
        return verifyHashesReturnError(df=df if isinstance(df, pd.DataFrame) else self.df, priorRowHash=priorRowHash)

    def verifyHashesReturnLastGood(self, df: pd.DataFrame = None, priorRowHash: str = '') -> tuple[bool, Union[pd.DataFrame, None]]:
        ''' passthrough for hashing verification '''
        return verifyHashesReturnLastGood(df=df if isinstance(df, pd.DataFrame) else self.df, priorRowHash=priorRowHash)

    def cleanByHashes(self, df: pd.DataFrame = None) -> tuple[bool, Union[pd.DataFrame, None]]:
        ''' passthrough for hash cleaning '''
        return cleanHashes(df=df if isinstance(df, pd.DataFrame) else self.df)

    def isARoot(self, df: pd.DataFrame) -> bool:
        ''' checks if the dataframe is a root '''
        return cleanHashes(df)[0]

    def hasRoot(self, df: pd.DataFrame) -> bool:
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return False
        return verifyRoot(df=df if isinstance(df, pd.DataFrame) else self.df)

    def matchesRoot(self, df: pd.DataFrame, localDf: pd.DataFrame = None) -> bool:
        ''' checks if the dataframe is a root '''
        localDf = localDf if localDf is not None else self.df
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
        self.updateCache(historyHashes(df or self.df))
        return self.write()

    def saveName(self) -> bool:
        ''' writes a readme.md file to disk describing dataset '''
        with open(self.path(filename='readme.md'), mode='w+') as f:
            file_data = f.read()
            if not file_data:
                f.write(self.id.topic())
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

    def overwriteClean(self) -> bool:
        success, result = self.cleanByHashes()
        if success == False and isinstance(result, pd.DataFrame):
            return self.overwrite(result)

    def overwrite(self, df: pd.DataFrame) -> bool:
        return self.csv.write(
            filePath=self.path(),
            data=self.updateCache(df))

    def write(self, df: pd.DataFrame = None) -> bool:
        return self.csv.write(
            filePath=self.path(),
            data=self.updateCache(self.hashDataFrame(
                self.updateCache(df) if df is not None else self.df)))

    def merge(self, df: pd.DataFrame) -> bool:
        ''' appends to the end of the file while also hashing '''
        if df is None or df.shape[0] == 0 or 'value' not in df.columns:
            return False
        if 'index' in df.columns:
            df = df.set_index('index')
        df = df.sort_index()
        if 'hash' not in df.columns:
            df['hash'] = ''
        if self.df.empty:
            self.loadCache()
            if self.df.empty:
                return self.write(df)
        self.df.update(df)  # update existing entries
        self.df = self.df.combine_first(df)  # add rows that are not in self.df
        return self.write(self.df)

    def append(self, df: pd.DataFrame, hashThis: bool = False) -> bool:
        ''' appends to the end of the file while also hashing '''
        if self.df.empty:
            self.loadCache()
            if self.df.empty:
                return self.write(df)
        if df is None or df.shape[0] == 0 or len(df.columns) > 2:
            return False
        if all([i in self.df.index for i in df.index]):
            return False
        df = df.sort_index()
        if 'hash' not in df.columns:
            if hashThis:
                df = self.hashDataFrame(
                    df=df,
                    priorRowHash=self.getHashBefore(df.index[0]))
            else:
                df['hash'] = ''
        combined = pd.concat([self.df, df])
        return self.csv.append(
            filePath=self.path(),
            data=self.updateCacheShowDifference(combined))

    def appendByAttributes(
        self,
        value: str,
        timestamp: str = None,
        observationHash: str = None,
        hashThis: bool = False,
    ) -> CachedResult:
        '''
        appends to the end of the file while also hashing,
        returns success and timestamp and observationHash
        '''
        timestamp = timestamp or datetimeToTimestamp(now())
        if timestamp in self.df.index:
            return CachedResult(
                success=False,
                time=timestamp,
                hash=observationHash,
                data=value)
        observationHash = observationHash or (
            hashIt(self.getHashBefore(timestamp) + str(timestamp) + str(value))
            if hashThis else '')
        df = pd.DataFrame(
            {'value': [value], 'hash': [observationHash]},
            index=[timestamp])
        if self.df.empty:
            self.loadCache()
            if self.df.empty:
                return CachedResult(
                    success=self.write(df),
                    time=timestamp,
                    hash=observationHash,
                    data=value,
                    validated=True)
        success = self.csv.append(
            filePath=self.path(),
            data=self.updateCacheShowDifference(pd.concat([self.df, df]))),
        validated, validatedFrame = self.performValidation()
        return CachedResult(
            time=timestamp,
            data=value,
            hash=observationHash,
            success=success,
            validated=validated,
            validatedFrame=validatedFrame)

    def performValidation(self, entire: bool = False) -> tuple[bool, Union[pd.DataFrame, None]]:
        ''' validates the hashes (efficiently using cached) returns results'''
        if self.df.empty:
            return True, None
        if entire:
            success, df = self.validateAllHashes()
        else:
            success, df = self.validateAllHashes(
                df=(self.df[self.df.index > self.checkedIndex]
                    if self.checkedIndex is not None else None),
                priorRowHash=self.checkedHash)
        return success, df

    def modifyBasedValidation(self, success: bool, df: Union[pd.DataFrame, None] = None):
        ''' modification done separately '''
        if success:
            self.checkedHash = self.df.iloc[-1].hash
            self.checkedIndex = self.df.index[-1]
        else:
            # logging.debug('validation failed', df, color='yellow')
            if df is None or df.empty:
                self.checkedHash = ''
                self.checkedIndex = None
            else:
                self.removeItAndAfter(df.index[-1])
                self.checkedHash = df.iloc[-1].hash
                self.checkedIndex = df.index[-1]
        return success

    def clear(self) -> Union[bool, None]:
        self.updateCacheSimple(self.df[0:0])
        self.csv.write(filePath=self.path(), data=self.df)

    def remove(self) -> Union[bool, None]:
        self.csv.remove(filePath=self.path())
        self.clearCache()

    def removeItAndAfter(self, timestamp) -> Union[bool, None]:
        self.updateCacheSimple(self.df[self.df.index < timestamp])
        self.csv.write(filePath=self.path(), data=self.df)

    def removeItAndBefore(self, timestamp) -> Union[bool, None]:
        self.updateCacheSimple(self.df[self.df.index > timestamp])
        self.csv.write(filePath=self.path(), data=self.df)

    ### read ###

    @property
    def cache(self) -> pd.DataFrame:
        if self.df.empty:
            self.loadCache()
        return self.df

    def loadCache(self) -> pd.DataFrame:
        return self.updateCache(self.read())

    def read(self, start: int = None, end: int = None) -> Union[pd.DataFrame, None]:
        if not self.exists():
            return None
        if start != None:
            return self.csv.readLines(
                filePath=self.path(),
                start=start,
                end=end).sort_index()
        return self.csv.read(filePath=self.path())

    def timeExistsInAggregate(self, time: str) -> bool:
        return isinstance(self.df, pd.DataFrame) and time in self.df.index

    def getRowCounts(self) -> int:
        ''' returns number of rows in incremental and aggregate tables '''
        if isinstance(self.df, pd.DataFrame):
            return self.df.shape[0]
        try:
            df = self.read()
            if isinstance(df, pd.DataFrame):
                return df.shape[0]
        except Exception as _:
            return 0

    def getHashBefore(self, time: str) -> str:
        ''' gets the hash of the observation just before a given time '''
        rows = self.search(time, before=True)
        if rows is None or rows.empty:
            return ''
        return rows.iloc[-1].hash

    def getObservationAfter(self, time: str) -> pd.DataFrame:
        ''' gets the observation just after a given time '''
        rows = self.search(time, after=True)
        if rows.empty:
            return rows
        return rows.iloc[[0]]

    def getObservationBefore(self, time: str) -> pd.DataFrame:
        ''' gets the observation just before a given time '''
        rows = self.search(time, before=True)
        if rows.empty:
            return rows
        return rows.iloc[[-1]]

    def getLatestObservationTime(self) -> str:
        ''' gets most recent time '''
        if self.df is None or self.df.empty:
            return datetimeToTimestamp(earliestDate())
        return self.df.sort_index().index.values[-1]

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
            df = (self if streamId == self.id else Cache(id=streamId)).read()
            if df is None:
                continue
            dfs.append(self.memory.expand(df=df, streamId=streamId))
        if len(dfs) == 0:
            return None
        if len(dfs) == 1:
            return dfs[0]
        return self.memory.merge(dfs=dfs, targetColumn=targetColumn)


class Cached:
    '''requires self.streamId attribute to be set'''

    def diskOf(self, streamId: StreamId) -> Cache:
        if not hasattr(self, '_diskOf') or self._diskOf is None or streamId != self._diskOf.id:
            from satorineuron.init.start import getStart
            self._diskOf = getStart().cacheOf(streamId)
        return self._diskOf

    @property
    def disk(self):
        if not hasattr(self, '_disk') or self._disk is None or self.streamId != self._disk.id:
            # circular import if outside this function. but it's ok here because
            # we take care to never call this function on imports or inits. and
            # this class is only used outside satorilib, such as in satorineuron
            # and satoriengine (which shouldn't import from neuron either, but
            # must in order to get the start singleton).
            from satorineuron.init.start import getStart
            self._disk = getStart().cacheOf(self.streamId)
            if not hasattr(self, '_disk') or self._disk is None:
                # logging.error(
                #    'self.disk for this stream missing, subscribed',
                #    self.streamId, self.streamId.generateHash)
                pass
        return self._disk

    @property
    def data(self) -> pd.DataFrame:
        return self.disk.cache

    @property
    def streamId(self) -> StreamId:
        return self._streamId

    @streamId.setter
    def streamId(self, value: StreamId):
        self._streamId = value
