from typing import Union, List
import pandas as pd
from sqlalchemy import create_engine, Table, MetaData, select, insert, delete
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from satorilib.api.interfaces.data import FileManager
from satorilib import logging

class SqliteManager(FileManager):
    ''' manages reading and writing to sqlite database using pandas '''

    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)
        self.metadata = MetaData()

    def _conform_basic(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._conform_index_name(self.conform_flat_columns(df))

    def _conform_index_name(self, df: pd.DataFrame) -> pd.DataFrame:
        df.index.name = 'id'
        return df

    def conform_flat_columns(self, df: pd.DataFrame) -> pd.DataFrame:
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

    def _merge(self, dfs: List[pd.DataFrame]) -> pd.DataFrame:
        return self._clean(pd.concat(dfs, axis=0))

    def remove(self, table_name: str) -> Union[bool, None]:
        try:
            table = Table(table_name, self.metadata, autoload_with=self.engine)
            table.drop(self.engine)
            return True
        except SQLAlchemyError as e:
            logging.error(f"Error removing table {table_name}", e, print=True)
            return False

    def read(self, table_name: str, **kwargs) -> pd.DataFrame:
        try:
            table = Table(table_name, self.metadata, autoload_with=self.engine)
            with self.Session() as session:
                result = session.execute(select(table))
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                return self._clean(self._conform_basic(df.set_index('id')))
        except SQLAlchemyError as e:
            logging.error(f"Error reading from table {table_name}", e, print=True)
            return None

    def write(self, table_name: str, data: pd.DataFrame) -> bool:
        try:
            data = self._conform_basic(data)
            data.to_sql(table_name, self.engine, if_exists='replace', index=True)
            return True
        except SQLAlchemyError as e:
            logging.error(f"Error writing to table {table_name}", e, print=True)
            return False

    def append(self, table_name: str, data: pd.DataFrame) -> bool:
        try:
            data = self._conform_basic(data)
            data.to_sql(table_name, self.engine, if_exists='append', index=True)
            return True
        except SQLAlchemyError as e:
            logging.error(f"Error appending to table {table_name}", e, print=True)
            return False

    def read_lines(self, table_name: str, start: int, end: int = None) -> Union[pd.DataFrame, None]:
        ''' 0-indexed '''
        end = (end if end is not None and end > start else None) or start + 1
        try:
            table = Table(table_name, self.metadata, autoload_with=self.engine)
            with self.Session() as session:
                query = select(table).order_by(table.c.id).offset(start).limit(end - start)
                result = session.execute(query)
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                return self._conform_basic(df.set_index('id'))
        except SQLAlchemyError as e:
            logging.error(f"Error reading lines from table {table_name}", e, print=True)
            return None