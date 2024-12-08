import pandas as pd


class DiskMemory():

    @staticmethod
    def merge(dfs: list[pd.DataFrame], targetColumn: 'str|tuple[str]'):
        ''' Layer 1
        combines multiple mutlicolumned dataframes.
        to support disparate frequencies, 
        outter join fills in missing values with previous value.
        filters down to the target column observations.
        '''
