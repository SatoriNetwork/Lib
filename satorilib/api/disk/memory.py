""" an api for reading and writing to disk """

import pandas as pd
from satorilib.api.time import datetimeToTimestamp, now
from satorilib.api.hash import hashIt
from satorilib.api.disk.cache import CachedResult
from satorilib.api.disk.filetypes.csv import CSVManager


def search(
    df: pd.DataFrame,
    time: str,
    before: bool = False,
    after: bool = False,
    exact: bool = False,
) -> pd.DataFrame:
    if not isinstance(time, str) or not any([before, after, exact]) or df is None:
        return None
    if before:
        return df[df.index < time]
    if after:
        return df[df.index > time]
    if exact:
        return df[df.index == time]
    return None


def getHashBefore(df: pd.DataFrame, time: str) -> str:
    """gets the hash of the observation just before a given time"""
    rows = search(df, time=time, before=True)
    if rows is None or rows.empty:
        return ""
    return rows.iloc[-1].hash
