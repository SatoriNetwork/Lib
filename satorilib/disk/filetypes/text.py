import pandas as pd
from satorilib.interfaces.data import FileManager


class TextManager(FileManager):
    ''' manages reading and writing to text files by python's `open` method '''

    def read(self, filePath: str):
        # Implement CSV file reading logic
        pass

    def write(self, filePath: str, data):
        # Implement CSV file writing logic
        pass

    def append(self, filePath: str, data):
        # Implement CSV file append logic
        pass

    def readLine(self, filePath: str, lineNumber: int):
        from itertools import islice
        with open(filePath, 'r') as file:
            try:
                line = next(islice(file, lineNumber - 1, lineNumber), None)
            except Exception as e:
                raise Exception(f'line number {lineNumber} not in file: {e}')
        return line.strip()

    def readLineWithHeaders(self, filePath: str, lineNumber) -> pd.DataFrame:
        ''' reads the first line and combines with the specified line to df '''
        from itertools import islice
        from io import StringIO
        firstLine = ''
        with open(filePath, 'r') as file:
            firstLine = file.readline()
            try:
                line = next(islice(file, lineNumber - 1, lineNumber), None)
            except Exception as e:
                raise Exception(f'line number {lineNumber} not in file: {e}')
        return pd.read_csv(StringIO("".join([firstLine.strip(), line.strip()])))
