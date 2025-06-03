from typing import Union
from enum import Enum
import pandas as pd
import time

def _generateCallId() -> str:
        return str(time.time())

class DataClientApi(Enum):
    '''the endpoint that data servers hit on the data client'''
    streamInactive = 'stream/inactive'
    streamObservation = 'stream/observation'

    def createResponse(
        self,
        uuid: str,
    ) -> dict:
        return {
                'status': self.value,
                'id': _generateCallId(),
                'params': {
                    'uuid': uuid,
                },
                'sub': True
            }
    
class DataServerApi(Enum):
    '''the endpoint that data clients (local/remote) hit on the data server'''
    initAuthenticate = 'client/initiate/auth'
    isLocalNeuronClient = 'client/neuron'
    isLocalEngineClient = 'client/engine'
    setPubsubMap = 'pubsub/set'
    getPubsubMap = 'pubsub/get'
    isStreamActive = 'stream/active/status'
    streamInactive= 'stream/inactive'
    subscribe = 'stream/subscribe'
    getStreamData = 'stream/data/get'
    getHash = 'stream/data/hash'
    getAvailableSubscriptions = 'streams/subscriptions/list'
    addActiveStream = 'stream/add'
    getStreamDataByRange = 'stream/data/get/range'
    getStreamObservationByTime = 'stream/observation/get/at'
    insertStreamData = 'stream/data/insert'
    deleteStreamData = 'stream/data/delete'
    unknown = 'unknown'
    statusSuccess = 'success'
    statusFail = 'failed'
    statusInactiveStream = 'inactive'
    
    def fromString(self, method: str) -> 'DataServerApi':
        ''' convert a string to a DataServerApi '''
        for api in DataServerApi:
            if api.value == method:
                return api
        #raise ValueError(f'Invalid method: {method}')
        return DataServerApi.unknown
    
    def remote(self) -> bool:
        ''' endpoints that can be called remotely '''
        return self in [
            DataServerApi.getPubsubMap,
            DataServerApi.isStreamActive,
            DataServerApi.subscribe,
            DataServerApi.getStreamData,
            DataServerApi.getAvailableSubscriptions,
            DataServerApi.getStreamDataByRange,
            DataServerApi.getStreamObservationByTime]
    
    def createRequest(
        self,
        uuid: Union[str, dict, None] = None,
        data: Union[pd.DataFrame, None] = None,
        replace: bool = False,
        fromDate: Union[str, None] = None,
        toDate: Union[str, None] = None,
        isSub: bool = False,
        auth: Union[dict, None] = None,
    ) -> dict:
        return {
                'method': self.value,
                'id': _generateCallId(),
                'sub': isSub,
                'params': {
                    'uuid': uuid,
                    'replace': replace,
                    'from_ts': fromDate,
                    'to_ts': toDate,
                },
                'data': data,
                'authentication': auth,
            }

    def createResponse(
        self,
        serverMsg: str,
        id: int,
        # uuid: Union[str, dict, list, None] = None,
        data: Union[pd.DataFrame, None] = None,
        streamInfo: Union[dict, list, str, None] = None,
        auth: Union[dict, None] = None,
        # isSub: bool = False,
    ) -> dict:
        return {
                'status': self.value,
                'message': serverMsg,
                'id': id or _generateCallId(),
                # 'params': {
                #     'uuid': uuid,
                # },
                'data': data,
                'authentication': auth,
                'stream_info': streamInfo
            }
    
