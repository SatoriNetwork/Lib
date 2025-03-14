import os
from typing import Union
import pandas as pd
import sqlite3
from . import sql_io


class Sqlite:
    '''
    Helpful wrapper object to access the sqlite functionality.
    Example:
    ```
    import Sqlite
    with Sqlite(database='path-to-db-file') as sql:

        # read
        df = sql.read(query='select * from table')

        # write using query
        sql.write(query="insert into table(col) values('foo')")

        # write dataframe
        sql.load(data=df, table='table', if_exists='append')

        # delete
        df = sql.delete(where="col='foo'", table='table')
    ```
    '''

    def __init__(
        self,
        database: str,
        initialize: str = None,
        index_col: str = None,
        lock=None,
    ):
        '''
        database - path to database file
        initialize - query to set up datbase tables first time
        '''
        self.database = database
        self.initialize = initialize or f'create table data ([column] text)'
        self.index_col = index_col
        self.lock = lock

    def __enter__(self):
        if not os.path.exists(os.path.abspath(self.database)):
            try:
                self.write(query=self.get_initialize())
            except sqlite3.OperationalError:
                # when distributed multiple machines may try to initialize
                pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    def get_initialize(self):
        return self.initialize

    def execute(
        self,
        query: str = None,
        params: Union[list[str], tuple[str, ...], dict[str, str], None] = None,
        data: pd.DataFrame = None,
        table: str = None,
        if_exists: str = 'append',
    ):
        if query:
            return sql_io.execute(
                lock=self.lock,
                query=query,
                # query=sql_io.apply_params(query, params),
                data=data,
                table=table,
                params=params or [],
                database=self.database,
                index_col=self.index_col)
        return sql_io.execute(
            lock=self.lock,
            data=data,
            table=table,
            if_exists=if_exists,
            database=self.database,
            index_col=self.index_col)

    def read(
        self,
        query: str = None,
        table: str = None,
        params: Union[list[str], tuple[str, ...], dict[str, str], None] = None,
    ):
        if query:
            return sql_io.read(
                # query=sql_io.apply_params(query, params),
                lock=self.lock,
                query=query,
                params=params,
                database=self.database,
                index_col=self.index_col)
        return sql_io.read(
            # query=sql_io.apply_params(f'select * from {table}', params),
            lock=self.lock,
            query='select * from ?',
            params=params or [table],
            database=self.database,
            index_col=self.index_col)

    def write(
        self,
        query: str,
        params: Union[list[str], tuple[str, ...], dict[str, str], None] = None,
    ):
        return sql_io.write(
            lock=self.lock,
            # query=sql_io.apply_params(query, params),
            query=query,
            params=params,
            database=self.database,
            index_col=self.index_col)

    def load(self, data: pd.DataFrame, table: str):
        return sql_io.write(
            lock=self.lock,
            data=data,
            table=table,
            database=self.database,
            index_col=self.index_col)

    def update(self, where: str, table: str, columns: list, values: list):
        return sql_io.update(
            lock=self.lock,
            where=where, table=table,
            columns=columns, values=values,
            database=self.database)

    def delete(self, where: str, table: str):
        return sql_io.delete(
            lock=self.lock,
            where=where,
            table=table,
            database=self.database)

    def drop(self, table: str):
        return sql_io.drop(
            lock=self.lock,
            table=table,
            database=self.database)
