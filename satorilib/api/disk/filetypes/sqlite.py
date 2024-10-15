from typing import Union
import os
import pandas as pd
from satorilib.api.interfaces.data import FileManager
from satorilib import logging


class CSVManager(FileManager):
    ''' manages reading and writing to CSV files usind pandas '''

    def _conformBasic(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._conformIndexName(self.conformFlatColumns(df))

    def _conformIndexName(self, df: pd.DataFrame) -> pd.DataFrame:
        df.index.name = None
        return df

    def conformFlatColumns(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df.columns) == 1:
            df.columns = ['value']
        if len(df.columns) == 2:
            df.columns = ['value', 'hash']
        return df

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._sort(self._dedupe(df))

    def _sort(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.sort_index()

    def _dedupe(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[~df.index.duplicated(keep='last')]

    def _merge(self, dfs: list[pd.DataFrame]) -> pd.DataFrame:
        return self._clean(pd.concat(dfs, axis=0))

    def remove(self, filePath: str) -> Union[bool, None]:
        try:
            os.remove(filePath)
            return True
        except FileNotFoundError as _:
            return None
        except Exception as _:
            return False

    def read(self, filePath: str, **kwargs) -> pd.DataFrame:
        try:
            return self._clean(self._conformBasic(pd.read_csv(filePath, index_col=0, header=None)))
        except Exception as _:
            # try:
            #    with open(filePath, mode='r') as f:
            #        x = f.read()
            #    if x != None and x != '' and x != ' ' and x != '\n':
            #        logging.info(
            #            f'unable to read file: {filePath}', e, f'filecontents: {x}', print=True)
            # except Exception as _:
            #    logging.info(
            #            f'unable to read file: {filePath}', e, print=True)
            return None

    def write(self, filePath: str, data: pd.DataFrame) -> bool:
        try:
            data.to_csv(filePath, header=False)
            return True
        except Exception as _:
            return False

    def append(self, filePath: str, data: pd.DataFrame) -> bool:
        try:
            data.to_csv(filePath, mode='a', header=False)
            return True
        except Exception as _:
            return False

    def readLines(
        self,
        filePath: str,
        start: int,
        end: int = None,
    ) -> Union[pd.DataFrame, None]:
        ''' 0-indexed '''
        end = (end if end is not None and end > start else None) or start+1
        capture = end - start - 1
        try:
            df = self._conformBasic(pd.read_table(
                filePath,
                sep=",",
                index_col=0,
                header=None,
                skiprows=start,
                # skipfooter=end, # slicing is faster; since using c engine
                # engine='python', # required for skipfooter
            ))
            return df.iloc[[capture]] if capture == 0 else df.iloc[0:capture+1]
        except Exception as e:
            logging.error('unable to get data', e, print=True)
            return None
