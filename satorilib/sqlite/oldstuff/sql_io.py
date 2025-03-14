import sqlite3
import pandas as pd
from .coerce import coerce
import threading


class MockLock:
    """ Mock Lock in case no Dask workers """

    def __init__(self, value):
        pass

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass


def execute(
    query: str = None,
    params: list = None,
    data: pd.DataFrame = None,
    table: str = None,
    if_exists: str = 'append',
    database: str = None,
    index_col: str = None,
    lock=None,
):
    if not query and data is None:
        return
    if lock is None:
        from dask.distributed import Lock
        lock = Lock('db-lock')
        try:
            with lock:
                pass
        except Exception:
            lock = MockLock('db-lock')
    with lock:
        with sqlite3.connect(database) as conn:
            if query:
                if ';' in query and (params is None or params == []):
                    return conn.executescript(query)
                else:
                    return conn.execute(query, params)
            if data is not None and table:
                if (not data.empty and data.columns.tolist() != [' ']) or data.empty:
                    return data.to_sql(
                        table, conn,
                        if_exists=if_exists,
                        index=True if index_col else False,
                        index_label=index_col if index_col else None)


def write(
    query: str = None,
    params: list = None,
    data: pd.DataFrame = None,
    table: str = 'dag_data',
    database=None,
    index_col=None,
    lock=None,
):
    ''' writes to a database table '''
    return execute(
        query=query,
        params=params,
        data=data,
        table=table,
        database=database,
        index_col=index_col,
        lock=lock)


def read(
    query: str,
    params: list = None,
    database=None,
    index_col=None,
    lock=None,
):
    ''' returns dataframe '''
    if lock is None:
        from dask.distributed import Lock
        lock = Lock('db-lock')
        try:
            with lock:
                pass
        except Exception:
            lock = MockLock('db-lock')
    with lock:
        with sqlite3.connect(database) as conn:
            if index_col:
                return pd.read_sql(query, conn, params=params, index_col=index_col)
            else:
                return pd.read_sql(query, conn, params=params)


def drop(table: str, database=None, lock=None):
    ''' drops a table '''
    # should not hide error? - defaults if exists functionality
    try:
        return execute(
            query=f'drop table {table};',
            database=database,
            lock=lock)
    except sqlite3.OperationalError:  # no such table
        return


def delete_query(where: str, table: str):
    return f"delete from {table} where {where}"


def delete(where: str, table: str, database=None, lock=None):
    ''' deletes a row from a table '''
    return execute(
        query=delete_query(where, table),
        database=database,
        lock=lock)


def update_query(where: str, columns: list, values: list, table: str):
    ''' returns query for updates '''
    columns = ",".join(coerce(columns, list))
    values = "','".join(coerce(values, list))
    return f"update {table} set {columns} = '{values}' where {where}"


def update(
    where: str,
    columns: list,
    values: list,
    table: str,
    database: str = None
):
    ''' returns query for updates '''
    query = update_query(
        where=where,
        columns=columns,
        values=values,
        table=table)
    return execute(
        query=query,
        database=database,
        lock=lock)


def apply_params(query: str, params: dict = None) -> str:
    if params:
        if '{{' in query:
            import jinja2
            query = jinja2.Template(query).render(**params)
        elif '{' in query:
            query = query.format(**params)
    return query
