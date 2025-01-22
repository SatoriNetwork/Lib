from typing import Union, Tuple
import websockets
import asyncio
import json


class Subscription:
    def __init__(
        self,
        #unique id?
        method: str,
        tableuuid: Union[list, None] = None,
        callback: Union[callable, None] = None
    ):
        self.method = method
        self.tableuuid = tableuuid
        self.shortLivedCallback = callback

    def __hash__(self):
        return hash((self.method, self.tableuuid))

    def __eq__(self, other):
        if isinstance(other, Subscription):
            return self.method == other.method and self.tableuuid == other.tableuuid
        return False

    def __call__(self, *args, **kwargs):
        '''
        This is the callback that is called when a subscription is triggered.
        it takes time away from listening to the socket, so it should be short-
        lived, like saving the value to a variable and returning, or logging,
        or triggering a thread to do something such as listen to the queue and
        do some long-running process with the data from the queue.
        example:
            def foo(*args, **kwargs):
                print(f'foo. args:{args}, kwargs:{kwargs}')
        '''
        if self.shortLivedCallback is None:
            return None
        return self.shortLivedCallback(*args, **kwargs)

class PeerInfo:

    def __init__(self, subscribersIp: list, publishersIp: list):
        self.subscribersIp = subscribersIp
        self.publishersIp = publishersIp

class ConnectedPeer:

    def __init__(
        self,
        hostPort: Tuple[str, int],
        websocket: websockets.WebSocketServerProtocol,
        subscriptions: Union[list, None] = None,
        publications: Union[list, None] = None,
    ):
        self.hostPort = hostPort
        self.websocket = websocket
        self.subscriptions = subscriptions or []
        self.publications = publications or []
        self.stop = asyncio.Event()

    @property
    def host(self):
        return self.hostPort[0]

    @property
    def port(self):
        return self.hostPort[1]

    @property
    def isClient(self):
        return self.hostPort[1] != 24602
    
    @property
    def isServer(self):
        return not self.isClient

    def add_subcription(self, table_uuid: str):
        self.subscriptions.append(table_uuid)


class Message:
    def __init__(self, message: dict):
        """
        Initialize Message object with a dictionary containing message data
        """
        self.message = message

    def to_dict(self) -> dict:
        """
        Convert the Message instance back to a dictionary
        """
        return {
            'method': self.method,
            'id': self.id,
            'sub': self.sub,
            'status': self.status,
            'params': {
                'table_uuid': self.table_uuid,
                'replace': self.replace,
                'from_ts': self.fromDate,
                'to_ts': self.toDate,
            },
            'data': self.data,
            'stream_info': self.streamInfo
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @property
    def method(self) -> str:
        """Get the method"""
        return self.message.get('method')

    @property
    def streamInfo(self) -> str:
        """Get the method"""
        return self.message.get('stream_info')
    
    @property
    def id(self) -> str:
        """Get the id UUID"""
        return self.message.get('id')

    @property
    def status(self) -> str:
        """Get the status"""
        return self.message.get('status')

    @property
    def sub(self) -> bool:
        """Get the sub"""
        return self.message.get('sub')

    @property
    def params(self) -> dict:
        """Get the params"""
        return self.message.get('params', {})

    @property
    def table_uuid(self) -> str:
        """Get the table_uuid from params"""
        return self.params.get('table_uuid')

    @property
    def replace(self) -> str:
        """Get the table_uuid from params"""
        return self.params.get('replace')

    @property
    def fromDate(self) -> str:
        """Get the table_uuid from params"""
        return self.params.get('from_ts')

    @property
    def toDate(self) -> str:
        """Get the table_uuid from params"""
        return self.params.get('to_ts')

    @property
    def subscriptionList(self) -> bool:
        """ server will indicate with True or False """
        return self.message.get('subscription-list')

    @property
    def data(self) -> any:
        """Get the data"""
        return self.message.get('data')

    @property
    def is_success(self) -> bool:
        """Get the status"""
        return self.status == 'success'
    
    @property
    def isSubscription(self) -> bool:
        """ server will indicate with True or False """
        return self.sub
        
    @property
    def isResponse(self) -> bool:
        """ server will indicate with True or False """
        return not self.isSubscription
    
