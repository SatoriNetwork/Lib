import sqlite3
import os
from typing import Dict, Any, List
from satorilib.utils import generateUUID
import pandas as pd
from pathlib import Path
from satorilib.logging import INFO, setup, debug, info, warning, error

setup(level=INFO)

class SqliteDatabase:
    def __init__(self, data_dir: str,dbname: str):
        self.conn = None
        self.cursor = None
        self.data_dir = data_dir
        self.dbname = os.path.join(data_dir, dbname)
        self.createConnection()

    def importFromDataFolder(self):
        """ Imports data from a structured data directory by scanning for README.md files and CSV data """
        
        def _getStreamInfoFromFolder() -> Dict:
            """ Scan all folders and extract stream info from README.md files """
            stream_infos = {}
            if not os.path.exists(self.data_dir):
                error("Data Folder does not exists")
                return {}
            for folder in os.listdir(self.data_dir):
                folder_path = Path(self.data_dir) / folder
                if folder_path.is_dir():
                    readme_path = folder_path / "readme.md"
                    if readme_path.exists(): 
                        stream_info = self._parseReadme(readme_path)
                        stream_infos[folder] = stream_info
                    else:
                        error(f"Skipping {folder}: No readme.md found")
            return stream_infos
        
        folder_stream_info = _getStreamInfoFromFolder()
        table_uuids = {folder: generateUUID(streaminfo) for folder, streaminfo in folder_stream_info.items()}
        for table_uuid in table_uuids.values():
            self.createTable(table_uuid)
        self.importCSVFromDataFolder(folder_stream_info, table_uuids)

    def createConnection(self):
        """ Creates or reopens a SQLite database connection with specific pragmas """
        try:
            if self.conn:
                self.conn.close()
            debug(f"Connecting to database at: {self.dbname}")
            os.makedirs(os.path.dirname(self.dbname), exist_ok=True)
            self.conn = sqlite3.connect(self.dbname)
            self.cursor = self.conn.cursor()
            self.cursor.execute('PRAGMA foreign_keys = ON;')
            self.cursor.execute('PRAGMA journal_mode = WAL;')
        except Exception as e:
            error("Connection error:", e)

    def disconnect(self):
        """ Closes the current database connection if one exists """
        if self.cursor:
            self.cursor.close()
            self.conn.close()

    def deleteDatabase(self):
        """ Deletes the SQLite database file from the filesystem """
        try:
            self.disconnect()
            if os.path.exists(self.dbname):
                os.remove(self.dbname)
        except Exception as e:
            error("Delete error:", e)

    def createTable(self, table_uuid: str):
        """ Create table with proper column types and quotes around table name """
        try:
            self.cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS "{table_uuid}" (
                    date_time TIMESTAMP PRIMARY KEY NOT NULL,
                    value NUMERIC(20, 10) NOT NULL,
                    id TEXT NOT NULL
                )
            ''')
            self.conn.commit()
        except Exception as e:
            error(f"Table creation error for {table_uuid}: ", e)

    def deleteTable(self, table_uuid: str):
        """ Deletes the table from the database """
        try:
            self.cursor.execute(f'DROP TABLE IF EXISTS "{table_uuid}"')
            self.conn.commit()
        except Exception as e:
            error(f"Table deletion error for {table_uuid}:", e)

    def editTable(self, action: str, table_uuid: str, data: Dict[str, Any] = None, timestamp: str = None):
        """ Edits a table's data based on the specified action """
        try:
            action = action.lower()
            if action == 'insert':
                self.cursor.execute(f'SELECT date_time FROM "{table_uuid}" WHERE date_time = ?', (data['date_time'],))
                existing = self.cursor.fetchone()
                if existing:
                    raise sqlite3.IntegrityError(f"Record with timestamp {existing[0]} already exists")
                cols = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                self.cursor.execute(f'INSERT INTO "{table_uuid}" ({cols}) VALUES ({placeholders})', list(data.values()))
                self.conn.commit()
                debug(f"Inserted new record into table {table_uuid}")
            elif action == 'update':
                if not timestamp:
                    raise ValueError("Timestamp is required for update operations")
                sets = ', '.join([f"{k} = ?" for k in data.keys()])
                values = list(data.values()) + [timestamp]
                self.cursor.execute(f'UPDATE "{table_uuid}" SET {sets} WHERE date_time = ?', values)
            elif action == 'delete':
                if not timestamp:
                    raise ValueError("Timestamp is required for delete operations")
                self.cursor.execute(f'DELETE FROM "{table_uuid}" WHERE date_time = ?', (timestamp,))
            else:
                error("Invalid choice, choose from : Insert, Update, Delete")

            if self.cursor.rowcount == 0 and action != 'insert':
                raise ValueError(f"No record found with timestamp {timestamp}")
            self.conn.commit()
        except sqlite3.IntegrityError as e:
            error(f"Database integrity error: {e}")
            self.conn.rollback()
        except Exception as e:
            error(f"{action.capitalize()} error for {table_uuid}: {e}")
            self.conn.rollback()
        finally:
            self._sortTableByTimestamp(table_uuid)
    
    def _sortTableByTimestamp(self, table_uuid: str):
        """ Sort the existing rows in a table by timestamp """
        try:
            temp_table = f'temp_{table_uuid}'
            self.cursor.execute(f'DROP TABLE IF EXISTS "{temp_table}"')
            self.cursor.execute(f'''
                CREATE TABLE "{temp_table}" (
                    date_time TIMESTAMP PRIMARY KEY NOT NULL,
                    value NUMERIC(20, 10) NOT NULL,
                    id TEXT NOT NULL
                )
            ''')
            self.cursor.execute(
                f'''
                INSERT INTO "{temp_table}" (date_time, value, id)
                SELECT date_time, value, id FROM "{table_uuid}"
                ORDER BY date_time ASC
            ''')
            self.cursor.execute(f'DROP TABLE IF EXISTS "{table_uuid}"')
            self.cursor.execute(f'ALTER TABLE "{temp_table}" RENAME TO "{table_uuid}"')
            self.conn.commit()
            debug(f"Successfully sorted table {table_uuid} by timestamp")
        except Exception as e:
            error(f"Error sorting table {table_uuid}: {e}")
            self.cursor.execute(f'DROP TABLE IF EXISTS "{temp_table}"')
            self.conn.commit()
            self.conn.rollback()
        
    def importCSVFromDataFolder(self, folder_metadata: dict, table_uuids: str):
        """ 
        Scan all folders in data directory and import their CSV files
        Assumes CSV files have no headers and columns are in order: timestamp, value, id 
        """

        if not os.path.exists(self.data_dir):
            raise Exception(f"Data directory not found: {self.data_dir}")
        imported_count = 0
        for folder_name in folder_metadata.keys():
            folder_path = Path(self.data_dir) / folder_name
            table_name = table_uuids.get(folder_name)
            if not table_name:
                debug(f"No table mapping found for folder: {folder_name}")
                continue
            csv_files = list(folder_path.glob('*.csv'))
            if not csv_files:
                continue
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file, header=None, names=['date_time', 'value', 'id'])
                    for _, row in df.iterrows():
                        self.cursor.execute(
                            f'''
                            SELECT 1 FROM "{table_name}" WHERE date_time = ? AND value = ? AND id = ?
                            ''', (row['date_time'], float(row['value']), str(row['id'])))
                        if not self.cursor.fetchone():
                            self.cursor.execute(f'INSERT INTO "{table_name}" (date_time, value, id) VALUES (?, ?, ?)', (row['date_time'], float(row['value']), str(row['id'])))
                    self.conn.commit()
                    imported_count += 1
                except Exception as e:
                    error(f"Error importing {csv_file}: {e}")
                    self.conn.rollback()
                    continue
        info(f"\nImport complete. Successfully processed {imported_count} CSV files.")
        
    def _importCSV(self, csv_path: str, readme_path: str):
        """ Import a single CSV file with its associated readme metadata """
        try:
            stream_dict = self._parseReadme(Path(readme_path))
            table_uuid = generateUUID(stream_dict)
            self.createTable(table_uuid)
            df = pd.read_csv(csv_path, header=None, names=['date_time', 'value', 'id'])
            imported_rows = 0
            for _, row in df.iterrows():
                self.cursor.execute(
                    f'''
                    SELECT 1 FROM "{table_uuid}" 
                    WHERE date_time = ? AND value = ? AND id = ?
                    ''', (
                        row['date_time'], 
                        float(row['value']), 
                        str(row['id'])
                    ))
                if not self.cursor.fetchone():
                    self.cursor.execute(
                        f'''
                        INSERT INTO "{table_uuid}" (date_time, value, id) 
                        VALUES (?, ?, ?)
                        ''', (
                            row['date_time'],
                            float(row['value']),
                            str(row['id'])
                        ))
                    imported_rows += 1
            self.conn.commit()
            if imported_rows > 0:
                info(f"New data was added, sorting table {table_uuid}")
                self._sortTableByTimestamp(table_uuid)
            else:
                info(f"No new data added to table {table_uuid}, skipping sort")     
        except Exception as e:
            error(f"Error importing CSV {csv_path}: {e}")
            self.conn.rollback()

    def _exportCSV(self, table_uuid: str, output_path: str = Path("./rec")): #Test
        """ Export data from a table to a CSV file """
        try:
            df = pd.read_sql_query(
                f'''
                SELECT date_time, value, id 
                FROM "{table_uuid}" 
                ORDER BY date_time
                ''', self.conn)
            
            if df.empty:
                warning(f"No data found in table {table_uuid}")
                return None
            output_path.mkdir(parents=True, exist_ok=True)
            csv_path = output_path / f"{table_uuid}.csv"
            df.to_csv(csv_path, header=False, index=False)
            info(f"Exported {len(df)} rows to {csv_path}")
        except Exception as e:
            error(f"Error exporting table {table_uuid}: {e}")
        
    def _parseReadme(self, readme_path: Path) -> Dict:
        """ Parse README.md file to return the stream details from it """
        import json
        try:
            with open(readme_path, 'r') as f:
                content = f.read().strip()
                if content:
                    json_data = json.loads(content)
                    if isinstance(json_data, dict):
                        return {
                            'source': json_data.get('source', ''),
                            'author': json_data.get('author', ''),
                            'stream': json_data.get('stream', ''),
                            'target': json_data.get('target', '')
                        }
        except Exception as e:
            error(f"Error parsing README {readme_path}: {e}")

    def _databasetoDataframe(self, table_uuid: str) -> pd.DataFrame:
        """ Converts a database table to a pandas DataFrame """
        try:
            self.cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
                """, (table_uuid,))
            if not self.cursor.fetchone():
                raise ValueError(f"Table {table_uuid} does not exist")
            df = pd.read_sql_query(
                f"""
                SELECT date_time, value, id 
                FROM "{table_uuid}"
                ORDER BY date_time
                """, self.conn)
            return df
        except ValueError as e:
            error(f"Table error: {e}")
        except Exception as e:
            error(f"Database error converting table {table_uuid} to DataFrame: {e}")

    def _dataframeToDatabase(self, table_uuid: str, df: pd.DataFrame):
        """ Writes a pandas DataFrame to a specified database table """
        try:
            self.cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
                """, (table_uuid,))
            if not self.cursor.fetchone():
                debug(f"Table {table_uuid} does not exist", print=True)
                self.createTable(table_uuid)
            required_columns = {'date_time', 'value', 'id'}
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"DataFrame must contain columns: {required_columns}")
            df['value'] = df['value'].astype(float)
            df['id'] = df['id'].astype(str)

            imported_rows = 0
            for _, row in df.iterrows():
                self.cursor.execute(
                    f'''
                    SELECT 1 FROM "{table_uuid}" 
                    WHERE date_time = ? AND value = ? AND id = ?
                    ''', (
                        row['date_time'],
                        float(row['value']),
                        str(row['id'])
                    ))
                if not self.cursor.fetchone():
                    self.cursor.execute(
                        f'''
                        INSERT INTO "{table_uuid}" (date_time, value, id) 
                        VALUES (?, ?, ?)
                        ''', (
                            row['date_time'],
                            float(row['value']),
                            str(row['id'])
                        ))
                    imported_rows += 1
            self.conn.commit()

            if imported_rows > 0:
                info(f"Added {imported_rows} new records to table {table_uuid}, sorting table")
                self._sortTableByTimestamp(table_uuid)
                return True
            else:
                info(f"No new data added to table {table_uuid}, skipping sort")    
        except ValueError as e:
            error(f"Validation error: {e}")
            self.conn.rollback()
        except Exception as e:
            error(f"Database error converting DataFrame to table {table_uuid}: {e}")
            self.conn.rollback()
            return False


if __name__ == "__main__":
    db = SqliteDatabase()


