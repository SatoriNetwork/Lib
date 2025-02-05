from typing import Union, Tuple
import websockets
import asyncio
import json


class Subscription:
    def __init__(
        self,
        uuid: str,
        callback: Union[callable, None] = None
    ):
        self.uuid = uuid
        self.shortLivedCallback = callback

    def __hash__(self):
        return hash(self.uuid)

    def __eq__(self, other):
        if isinstance(other, Subscription):
            return self.uuid == other.uuid
        return False

    async def __call__(self, *args, **kwargs):
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
        return await self.shortLivedCallback(self, *args, **kwargs)


class PeerInfo:

    def __init__(self, subscribersIp: list, publishersIp: list):
        self.subscribersIp = subscribersIp
        self.publishersIp = publishersIp


class Peer:
    def __init__(self, ip: str, port: int) -> None:
        self.ip = ip
        self.port = port
    
    def __eq__(self, value: 'Peer') -> bool:
        return self.ip == value.ip and self.port == value.port

    def __str__(self) -> str:
        return str(self.asTuple)
    
    def __hash__(self) -> int:
        return hash((self.ip, self.port))

    def __repr__(self) -> str:
        return self.ip, self.port

    @property
    def asTuple(self) -> tuple[str, int]:
        return self.__repr__()


class ConnectedPeer:

    def __init__(
        self,
        hostPort: Tuple[str, int],
        websocket: websockets.WebSocketServerProtocol,
        subscriptions: Union[set[str], None] = None, # the streams that this client subscribes to (from my server)
        publications: Union[set[str], None] = None, # the streams that this client publishes (to my server)
        isNeuron: bool = False,
        isEngine: bool = False,
    ):
        self.hostPort = hostPort
        self.websocket = websocket
        self.subscriptions: set[str] = subscriptions or set()
        self.publications: set[str] = publications or set()
        self.isNeuron = isNeuron
        self.isEngine = isEngine
        self.listener = None
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
    
    @property
    def isLocal(self) -> bool:
        return self.isEngine or self.isNeuron
    
    def add_subscription(self, uuid: str):
        self.subscriptions.add(uuid)

    def add_publication(self, uuid: str):
        self.publications.add(uuid)

    def remove_subscription(self, uuid: str) -> bool:
        """
        Remove a subscription if it exists.
        Returns True if the subscription was removed, False if it wasn't found.
        """
        existed = uuid in self.subscriptions
        self.subscriptions.discard(uuid)
        return existed

    def remove_publication(self, uuid: str) -> bool:
        """
        Remove a publication if it exists.
        Returns True if the publication was removed, False if it wasn't found.
        """
        existed = uuid in self.publications
        self.publications.discard(uuid)
        return existed
        

class Message:

    def __init__(self, message: dict):
        """
        Initialize Message object with a dictionary containing message data
        """
        self.message = message

    def to_dict(self, isResponse: bool = False) -> dict:
        """
        Convert the Message instance back to a dictionary
        """
        if isResponse:
            return {
            'status': self.status,
            'message': self.senderMsg,
            'id': self.id,
            # 'sub': self.sub,
            'params': {
                'uuid': self.uuid,
            },
            'data': self.data,
            'stream_info': self.streamInfo
        }
        return {
            'method': self.method,
            'id': self.id,
            'sub': self.sub,
            'status': self.status,
            'params': {
                'uuid': self.uuid,
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
    def senderMsg(self) -> str:
        """Get the method"""
        return self.message.get('message')
    
    @property
    def id(self) -> str:
        """Get the id UUID"""
        return self.message.get('id')

    @property
    def status(self) -> str:
        """Get the status"""
        return self.message.get('status')
    
    @property
    def statusMsg(self) -> str:
        """Get the status"""
        return self.message.get('message')

    @property
    def sub(self) -> bool:
        """Get the sub"""
        return self.message.get('sub')

    @property
    def params(self) -> dict:
        """Get the params"""
        return self.message.get('params', {})

    @property
    def uuid(self) -> str:
        """Get the uuid from params"""
        return self.params.get('uuid')

    @property
    def replace(self) -> str:
        """Get the uuid from params"""
        return self.params.get('replace')

    @property
    def fromDate(self) -> str:
        """Get the uuid from params"""
        return self.params.get('from_ts')

    @property
    def toDate(self) -> str:
        """Get the uuid from params"""
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
    
