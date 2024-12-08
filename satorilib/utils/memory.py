from functools import reduce
import pandas as pd
import warnings
from satorilib import logging
from satorilib.concepts import StreamId
from satorilib.interfaces.memory import DiskMemory
from satorilib.interfaces.model import ModelMemoryApi

warnings.simplefilter(action='ignore', category=FutureWarning)


class Memory(ModelMemoryApi, DiskMemory):

    @staticmethod
    def flatten(df: pd.DataFrame):
        '''
        on disk we store dataframes as flat, with an index, and
        [value, hash, prediction] columns, but in memory we always combine
        datasets into one multi-columned dataframe, so we need to flatten the
        dataframe before saving to disk
        '''
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel()  # source
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel()  # author
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel()  # stream
        # if isinstance(df.columns, pd.MultiIndex):
        #    df.columns = df.columns.droplevel()  # target
        return df

    @staticmethod
    def expand(df: pd.DataFrame, streamId: StreamId) -> pd.DataFrame:
        ''' makes a flat dataframe into a multilayered column dataframe '''
        if 'hash' in df.columns:
            df.drop(columns='hash', inplace=True)
        cols = df.columns
        if len(cols) == 1 and cols == 'value':
            cols = [streamId.target]
        df.columns = pd.MultiIndex.from_product(
            [[streamId.source], [streamId.author], [streamId.stream], cols])
        return df.sort_index()

    @staticmethod
    def mergeAllTime(dfs: list[pd.DataFrame]):
        ''' Layer 1 - not useful?
        combines multiple mutlicolumned dataframes.
        to support disparate frequencies,
        outter join fills in missing values with previous value.
        So this isn't really important anymore becauase I realized
        it'll not be needed anywhere I think, maybe for the live
        updates models and stream but that's for later.
        '''
        if dfs is pd.DataFrame:
            return dfs
        if len(dfs) == 0:
            return None
        if len(dfs) == 1:
            return dfs[0]
        for df in dfs:
            df.index = pd.to_datetime(df.index)
        return reduce(
            lambda left, right: pd.merge(
                left,
                right,
                how='outer',
                left_index=True,
                right_index=True)
            # can't use this for merge because we don't want to fill the targetColumn
            .fillna(method='ffill'),
            # .fillna(method='bfill'),
            # don't bfill here, in many cases its fine to bfill, but not in all.
            # maybe we will bfill in model. always bfill After ffill.
            dfs)

    @staticmethod
    def merge(dfs: list[pd.DataFrame], targetColumn: 'str|tuple[str]'):
        ''' Layer 1
        combines multiple mutlicolumned dataframes.
        to support disparate frequencies,
        outter join fills in missing values with previous value.
        filters down to the target column observations.
        '''
        if len(dfs) == 0:
            return None
        if len(dfs) == 1:
            return dfs[0]
        for ix, item in enumerate(dfs):
            if targetColumn in item.columns:
                dfs.insert(0, dfs.pop(ix))
                break
            # if we get through this loop without hitting the if
            # we could possibly use that as a trigger to use the
            # other merge function, also if targetColumn is None
            # why would we make a dataset without target though?
        for df in dfs:
            df.index = pd.to_datetime(df.index)
        return reduce(
            lambda left, right:
                pd.merge_asof(left, right, left_index=True, right_index=True),
            dfs)

    @staticmethod
    def appendInsert(df: pd.DataFrame, incremental: pd.DataFrame):
        ''' Layer 2
        after datasets merged one cannot merely append a dataframe.
        we must insert the incremental at the correct location.
        this function is more of a helper function after we gather,
        to be used by models, it doesn't talk to disk directly.
        incremental should be a multicolumn, one row DataFrame.
        '''
        df.index = pd.to_datetime(df.index)
        incremental.index = pd.to_datetime(incremental.index)
        if incremental.index.values[0] in df.index.values:
            df.loc[incremental.index, [
                x for x in incremental.columns]] = incremental
        else:
            df = df.append(incremental).sort_index()
        return df.fillna(method='ffill')

    @staticmethod
    def dropDuplicates(df: pd.DataFrame, col=None):
        if df.empty:
            return df

        if isinstance(df.columns, pd.MultiIndex):
            # supports the typical hierarchy of source, author, stream, target
            column = (
                ('group',) +
                tuple(('' for _ in range(1, len(df.columns[0])))))
        else:
            # unused edgecase - normal index columns
            column = 'group'

        if len(df.columns) > 1 and col is None:
            logging.error('must provide column')
            return df
        elif len(df.columns) > 1 and col is not None:
            # unused edgecase - multiple columns in dataframe
            df[column] = (df[col] != df[col].shift()).cumsum()
            df = df.drop_duplicates(subset=column, keep='first')
            df = df.drop(columns=[column])
            return df

        # Create a new grouping column based on consecutive duplicates
        df[column] = (df != df.shift()).cumsum()
        # Drop duplicates based on groups, keeping the first occurrence
        df = df.drop_duplicates(subset=column, keep='first')
        # Drop the grouping column
        df = df.drop(columns=[column])
        return df
