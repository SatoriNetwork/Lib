#!/usr/bin/env python
# coding: utf-8

''' an api for reading and writing to disk '''

from typing import Union, Tuple
import os
import shutil
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from satorilib import logging
from satorilib.concepts import StreamId
from satorilib.api import memory
from satorilib.api import hash
from satorilib.api.interfaces.data import DataDiskApi
from satorilib.api.interfaces.model import ModelDataDiskApi
from satorilib.api.disk.utils import safetify, safetifyWithResult
from satorilib.api.disk.model import ModelApi
from satorilib.api.disk.wallet import WalletApi


class Disk(DataDiskApi, ModelDataDiskApi):
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
        ext: str = 'parquet',
        **kwargs,
    ):
        self.memory = memory.Memory
        self.setAttributes(df=df, id=id, loc=loc, ext=ext, **kwargs)

    def setAttributes(
        self,
        df: pd.DataFrame = None,
        id: StreamId = None,
        loc: str = None,
        ext: str = 'parquet',
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

    def safetify(self, path: str):
        path, created = safetifyWithResult(path)
        if created:
            self.saveName()
        return path

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

    def setId(self, id: StreamId = None):
        self.id = id

    def path(self, aggregate: Union[bool, type[None]] = False, temp: bool = False):
        ''' Layer 0
        get the path of a file
        we generate a hash as the id for the datastream so we can store it in a
        folder and avoid worrying about path length limits. also, we can use the
        entire folder as the ipfs hash for the datastream.
        path lengths should about 170 characters long typically. for examples:
        C:\\Users\\user\\AppData\\Local\\Satori\\models\\qZk-NkcGgWq6PiVxeFDCbJzQ2J0=.joblib
        C:\\Users\\user\\AppData\\Local\\Satori\\data\\qZk-NkcGgWq6PiVxeFDCbJzQ2J0=\\aggregate.parquet
        C:\\Users\\user\\AppData\\Local\\Satori\\data\\qZk-NkcGgWq6PiVxeFDCbJzQ2J0=\\incrementals\\6c0a15fcfa1c4535ab1da046cc1b5dc8.parquet
        '''
        if isinstance(aggregate, str):
            filename = aggregate
        elif aggregate == False:
            filename = 'incrementals/'
        elif aggregate == None:
            filename = ''
        elif aggregate:
            filename = f'aggregate.{self.ext}'
        else:
            filename = 'incrementals/'
        return self.safetify(os.path.join(
            self.loc or (Disk.config.tempPath()
                         if temp else Disk.config.dataPath()),
            hash.generatePathId(streamId=self.id),
            filename))

    def exists(self, aggregate: bool = False, temp: bool = False):
        ''' Layer 0 return True if file exists at path, else False '''
        return os.path.exists(self.path(aggregate, temp=temp))

    def reduceMulti(self, df: pd.DataFrame):
        ''' Layer 0 '''
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel()  # source
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel()  # author
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel()  # stream
        # if isinstance(df.columns, pd.MultiIndex):
        #    df.columns = df.columns.droplevel()  # target
        return df

    def toTable(self, df: pd.DataFrame = None):
        ''' Layer 0 '''
        return pa.Table.from_pandas(self.reduceMulti(df if df is not None else self.df))

    def incrementals(self):
        ''' Layer 0 '''
        return os.listdir(self.path())

    def saveName(self):
        ''' Layer 1
        writes a readme.md file to disk describing dataset
        '''
        with open(self.path(aggregate='readme.md'), mode='w+') as f:
            file_data = f.read()
            if not file_data:
                f.write(self.id.topic())

    def append(self, df: pd.DataFrame = None):
        ''' Layer 1
        writes a dataframe to a parquet file.
        must remove multiindex column first.
        must use write_to_dataset rather than write_to_table to support append.
        streamId is the name of file.
        '''
        pq.write_to_dataset(self.toTable(df), self.path())

    def write(self, df: pd.DataFrame = None):
        ''' Layer 1
        writes a dataframe to a parquet file.
        must remove multiindex column first.
        streamId is the name of file.
        '''
        pq.write_table(self.toTable(df), self.path(aggregate=True))

    def compress(self, includeTemp=False, download=None):
        ''' Layer 1
        assumes columns are always the same...
        this function is used on rare occasion to compress the on disk
        incrementally saved data to long term storage. The compressed
        table takes up less room than the dataset because the dataset
        is partitioned into many files, allowing us to easily append
        to it. So we normally append observations to the dataset, and
        occasionally, like daily or weekly, run this compress function
        to save it to long term storage. We can still query long term
        storage the same way.

        this function can take some amount of time since it has to read data 
        from disk and merge it. while it is running we might get a new update,
        which would then automatically be saved to disk in another thread, and
        removed before writing the df. Oops. this is why we take the incremental
        count before reading the data, and then check it again after the merge,
        and if it has changed we just restart the whole process. nothing, 
        therefore, should wait for this to complete.
        '''
        incCount = len(self.incrementals())
        df = self.readBoth()
        if includeTemp:
            existing = df
            download = download if download is not None else self.readBoth(
                temp=True)
            df = self.merge(existing, download)
        if df is not None:
            if incCount == len(self.incrementals()):
                self.remove()
                if includeTemp:
                    self.remove(temp=True)
                self.write(df)
            else:
                self.compress(includeTemp=includeTemp, download=download)

    def remove(self, aggregate: bool = None, temp: bool = False, time: float = None):
        ''' Layer 1 
        removes the aggregate or incremental tables from disk
        '''
        if aggregate is None:
            self.remove(True, temp=temp, time=time)
            self.remove(False, temp=temp, time=time)
        targetPath = self.path(aggregate, temp=temp)
        if aggregate:
            if (self.exists(aggregate, temp=temp) and (
                        time is None or (
                            os.stat(targetPath).st_mtime < time and
                            os.path.isfile(targetPath)))
                    ):
                try:
                    os.remove(targetPath)
                except FileNotFoundError as e:
                    logging.warning(
                        f'Agg File not found unable to remove. Ignoring {e}')
        else:
            if time is None:
                shutil.rmtree(targetPath, ignore_errors=True)
            else:
                for f in os.listdir(targetPath):
                    f = os.path.join(targetPath, f)
                    if os.stat(f).st_mtime < time and os.path.isfile(f):
                        try:
                            os.remove(f)
                        except FileNotFoundError as e:
                            logging.warning(
                                f'File not found unable to remove. Ignoring {e}')

    def readBoth(self, **kwargs):
        ''' Layer 1 
        read both the aggregate and incremental tables into memory
        merge them into one dataframe
        '''
        inc = self.read(aggregate=False, **kwargs)
        agg = self.read(aggregate=True, **kwargs)
        return self.merge(inc, agg)

    def merge(self, inc: pd.DataFrame, agg: pd.DataFrame):
        ''' Layer 1 
        meant to merge long term (aggregate) written tables 
        with short term (incremental) appended datasets
        for one stream
        '''
        if (inc is None or inc.empty) and (agg is None or agg.empty):
            return None
        if inc is None or inc.empty:
            return self.memory.dropDuplicates(agg)
        if agg is None or agg.empty:
            return self.memory.dropDuplicates(inc)
        inc['TempIndex'] = inc.index
        agg['TempIndex'] = agg.index
        inc = inc.apply(lambda col: pd.to_numeric(col, errors='ignore'))
        agg = agg.apply(lambda col: pd.to_numeric(col, errors='ignore'))
        df = pd.merge(inc, agg, how='outer', on=list(inc.columns))
        df.index = df['TempIndex']
        df.index.name = None
        df = df.drop('TempIndex', axis=1, level=0)
        return self.memory.dropDuplicates(df.sort_index())

    def read(self, aggregate: bool = None, **kwargs) -> pd.DataFrame:
        ''' Layer 1
        reads a parquet file with filtering, use columns=[targets].
        adds on the stream as first level in multiindex column on dataframe.
        Since we compress incremental observations into long term storage we
        really have 2 datasets per stream to look up, thus we specify aggregate
        as None in order to pull from both datasets and merge automatically.
        '''
        source = self.id.source or self.df.columns.levels[0]
        author = self.id.author or self.df.columns.levels[1]
        stream = self.id.stream or self.df.columns.levels[2]
        try:
            target = self.id.target or self.df.columns.levels[3]
        except AttributeError:
            logging.debug('no target. thats cool?')
        if aggregate is None:
            return self.readBoth(**kwargs)
        if not self.exists(aggregate):
            return None
        rdf: pd.DataFrame = pq.read_table(self.path(aggregate)).to_pandas()
        # if column is 'value' make it the target so we can merge.
        cols = rdf.columns
        if len(cols) == 1 and cols == 'value':
            cols = [target]
        rdf.columns = pd.MultiIndex.from_product(
            [[source], [author], [stream], cols])
        return rdf.sort_index()

    # not possible, even using read_row_group is weird because its like 128-1gb
    # chunks at a time... so if we ever do anything with that we'll do it later.
    # def readOneRowFromAggregate(self, rowNumber=0):
    #    ''' just read in the values without messing with columns '''
    #    return (
    #        pq.ParquetFile(self.path(aggregate=True))
    #        .read_row(row_number=rowNumber))

    def timeExistsInAggregate(self, time: str) -> bool:
        '''example: 
        >>> '2023-05-31 18:13:46.309658' in (pq
            .ParquetFile('../mt8n5T6TF2H2qQLp-6aQQTnoGYs=/aggregate.parquet')
            .read(columns=['__index_level_0__'])
            .to_pandas().index)
        '''
        return time in (
            pq
            .ParquetFile(self.path(aggregate=True))
            .read(columns=['__index_level_0__'])
            .to_pandas().index)

    def getRowCounts(self, aggregate: bool = None) -> int:
        ''' returns number of rows in incremental and aggregate tables '''
        if aggregate is None:
            return (
                self.getRowCounts(aggregate=False) +
                self.getRowCounts(aggregate=True))
        elif aggregate:
            try:
                return (
                    pq.ParquetFile(self.path(aggregate=True)).metadata.num_rows)
            except Exception as _:
                return 0
        else:
            try:
                return self.read(aggregate=False).shape[0]
            except Exception as _:
                return 0

    def savePrediction(self, path: str = None, prediction: str = None):
        ''' Layer 1 - saves prediction to disk '''
        safetify(path)
        with open(path, 'a') as f:
            f.write(prediction)

    def gather(
        self,
        targetColumn: 'str|tuple[str]',
        streamIds: list[StreamId] = None,
    ):
        ''' Layer 2. 
        retrieves the targets and merges them.
        '''
        def filterNone(items: list):
            return [x for x in items if x is not None]

        if streamIds is not None:
            items = []
            for streamId in streamIds:
                self.setId(id=streamId)
                items.append(self.read(columns=streamId.target))
            return self.memory.merge(
                dfs=filterNone(items),
                targetColumn=targetColumn)
        return self.read()

    # # this is not good. we don't want to open the file from disk every time we
    # # are quiried. instead, just keep it in memory (either in the engine data
    # # manager or in the rendezvous topic) and pull it from there on demand.
    # def lastRowStringBefore(self, streamId: StreamId, timestamp: str) -> Union[Tuple[str, str], None]:
    #    """
    #    Opens a parquet file and returns the latest row before a given timestamp.
    #
    #    Parameters:
    #        streamId (StreamId): used to define path to the parquet file.
    #        timestamp (str or pd.Timestamp): The target timestamp to find the latest row before.
    #
    #    Returns:
    #        str or None: The latest row before the target timestamp, or None if no matching row is found.
    #    """
    #    def rowToString(row: pd.Series):
    #        return row.name, row.values[0]
    #
    #    def singleRowToString(row: pd.DataFrame):
    #        return row.index[0], row.values[0]
    #
    #    # is this even necessary?
    #    # if not isinstance(timestamp, pd.Timestamp):
    #    #    timestamp = pd.Timestamp(timestamp)
    #
    #    # try to get it from the incrementals first
    #    df = self.read(aggregate=False)
    #    maxTimestampBefore = df.index[df.index < timestamp].max()
    #    if str(maxTimestampBefore) != 'nan':
    #        return singleRowToString(df.loc[df.index == maxTimestampBefore])
    #    # if not found in incrementals, try to get it from the aggregate:
    #    filterCondition = ('__index_level_0__', '<', f'{timestamp}')
    #    table = pq.read_table(
    #        self.path(streamId),
    #        filters=[filterCondition],
    #        use_pandas_metadata=True)
    #    # If no rows are found, return None
    #    if len(table) == 0:
    #        return None
    #    # maybe this solution can be used to get it directly from disk, but no.
    #    # batch = next(pf.iter_batches(batch_size = 1))
    #    # row = pa.Table.from_batches([batch]).to_pandas()
    #    df = table.to_pandas()
    #    return rowToString(df.loc[df.index.max()])  # series


'''
from satorineuron.lib.apis import disk
x = disk.Api(source='streamrSpoof', stream='simpleEURCleaned') 
df = x.read()
df
x.read(columns=['High'])
exit()

'''
