from typing import Union
from enum import Enum


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
    
    def fromString(self, method: str) -> 'DataServerApi':
        ''' convert a string to a DataServerApi '''
        for api in DataServerApi:
            if api.value == method:
                return api
        #raise ValueError(f'Invalid method: {method}')
        return api.unknown
    
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