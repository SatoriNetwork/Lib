import pandas as pd
from satorilib.concepts import StreamId


class ModelMemoryApi():
    @staticmethod
    def appendInsert(df: pd.DataFrame, incremental: pd.DataFrame):
        ''' Layer 2
        after datasets merged one cannot merely append a dataframe. 
        we must insert the incremental at the correct location.
        this function is more of a helper function after we gather,
        to be used by models, it doesn't talk to disk directly.
        incremental should be a multicolumn, one row DataFrame. 
        '''


class ModelDataDiskApi():
    @staticmethod
    def defaultModelPath(streamId: StreamId):
        ''' returns the path to the model '''

    @staticmethod
    def saveModel(model, modelPath: str = None, hyperParameters: list = None, chosenFeatures: list = None):
        ''' saves model using ModelDiskApi'''

    @staticmethod
    def loadModel(model):
        ''' loads model using ModelDiskApi'''

    def gather(
        self,
        targetColumn: 'str|tuple[str]',
        streamIds: list[StreamId] = None,
    ):
        ''' Layer 2. 
        retrieves the targets and merges them.
        as a prime example of premature optimization I made 
        this function callable in a myriad of various ways...
        I don't remember why.
        '''


class ModelDiskApi(object):

    @staticmethod
    def save(model, modelPath: str = None, hyperParameters: list = None, chosenFeatures: list = None):
        ''' saves model to disk '''

    @staticmethod
    def load(modelPath: str = None):
        ''' loads model from disk '''
