from typing import Union
from enum import Enum
import pandas as pd
import time


class DataClientApi(Enum):
    '''the endpoint that data servers hit on the data client'''
    streamInactive = 'stream/inactive'
    streamObservation = 'stream/observation'
    
class DataServerApi(Enum):
    '''the endpoint that data clients (local/remote) hit on the data server'''
    isLocalNeuronClient = 'client/neuron'
    isLocalEngineClient = 'client/engine'
    setPubsubMap = 'pubsub/set'
    getPubsubMap = 'pubsub/get'
    isStreamActive = 'stream/active/status'
    streamInactive= 'stream/inactive'
    subscribe = 'stream/subscribe'
    getStreamData = 'stream/data/get'
    getAvailableSubscriptions = 'streams/subscriptions/list'
    addActiveStream = 'stream/add'
    getStreamDataByRange = 'stream/data/get/range'
    getStreamObservationByTime = 'stream/observation/get/at'
    insertStreamData = 'stream/data/insert'
    deleteStreamData = 'stream/data/delete'
    unknown = 'unknown'
    
    @staticmethod
    def _generateCallId() -> str:
        return str(time.time())
        
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
        uuid: str = None,
        data: pd.DataFrame = None,
        replace: bool = False,
        fromDate: str = None,
        toDate: str = None,
        isSub: bool = False,
    #     rawMsg: Message = None,
    ) -> dict:
        return {
                'method': self,
                'id': self._generateCallId(),
                'sub': isSub,
                'params': {
                    'uuid': uuid,
                    'replace': replace,
                    'from_ts': fromDate,
                    'to_ts': toDate,
                },
                'data': data.to_json() if data is not None else None,
            }
    
    # def createSubscriptionRequest(
    #     self,
    #     uuid: str,
    #     data: pd.DataFrame = None,
    #     replace: bool = False,
    #     fromDate: str = None,
    #     toDate: str = None,
    # ) -> dict:
    #     return {
    #             'method': self,
    #             'id': self._generateCallId(),
    #             'sub': False,
    #             'params': {
    #                 'uuid': uuid,
    #                 'replace': replace,
    #                 'from_ts': fromDate,
    #                 'to_ts': toDate,
    #             },
    #             'data': data,
    #         }
    
    # def passObservationRequest(
    #     self,
    #     uuid: str,
    #     data: pd.DataFrame,
    # ) -> dict:
    #     return {
    #             'method': self,
    #             'id': self._generateCallId(),
    #             'sub': True,
    #             'params': {
    #                 'uuid': uuid,
    #                 'replace': False,
    #                 'from_ts': None,
    #                 'to_ts': None,
    #             },
    #             'data': data.to_json(orient='split'),
    #         }
    
    # def authenticationRequest(
    #     self,
    # ) -> dict:
    #     return {
    #             'method': self,
    #             'id': self._generateCallId(),
    #             'sub': False,
    #             'params': {
    #                 'uuid': None,
    #                 'replace': False,
    #                 'from_ts': None,
    #                 'to_ts': None,
    #             },
    #             'data': None,
    #         }






















