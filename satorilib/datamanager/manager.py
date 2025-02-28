import pandas as pd
from satorilib.logging import debug, error
from satorilib.sqlite import SqliteDatabase
from typing import Union


class DataManager:
    def __init__(
        self,
        db_path: str = "../../data",
        db_name: str = "data.db",
    ):
        self.pubSubMapping: dict[str, dict] = {}
        self.transferProtocolFlag: Union[dict, None] = None
        self.db = SqliteDatabase(db_path, db_name)
        self.db.importFromDataFolder()  # can be disabled if new rows are added to the Database and new rows recieved are inside the database

    def getStreamData(self, uuid: str) -> pd.DataFrame:
        """Get data for a specific stream directly from SQLite database"""
        try:
            df = self.db._databasetoDataframe(uuid)
            if df is None or df.empty:
                debug("No data available to send")
                return pd.DataFrame()
            return df
        except Exception as e:
            error(f"Error getting data for stream {uuid}: {e}")

    def getStreamDataByDateRange(
        self, uuid: str, from_date: str, to_date: str
    ) -> pd.DataFrame:
        """Get stream data within a specific date range (inclusive)"""
        try:
            df = self.db._databasetoDataframe(uuid)
            if df is None or df.empty:
                debug("No data available to send")
                return pd.DataFrame()
            from_ts = pd.to_datetime(from_date)
            to_ts = pd.to_datetime(to_date)
            df.index = pd.to_datetime(df.index)
            filtered_df = df[(df.index >= from_ts) & (df.index <= to_ts)]
            return filtered_df if not filtered_df.empty else pd.DataFrame()
        except Exception as e:
            error(f"Error getting data for stream {uuid} in date range: {e}")

    def getLastRecordBeforeTimestamp(
        self, uuid: str, timestamp: str
    ) -> pd.DataFrame:
        """Get the last record before the specified timestamp (inclusive)"""
        try:
            df = self.db._databasetoDataframe(uuid)
            if df is None or df.empty:
                return pd.DataFrame()
            ts = pd.to_datetime(timestamp)
            df.index = pd.to_datetime(df.index)
            if not df.loc[df.index == ts].empty:  # First check for exact match
                return df.loc[df.index == ts]
            before_ts = df.loc[
                df.index < ts
            ]  # check for timestamp before specified timestamp
            return before_ts.iloc[[-1]] if not before_ts.empty else pd.DataFrame()
        except Exception as e:
            error(
                f"Error getting last record before timestamp for stream {uuid}: {e}"
            )
