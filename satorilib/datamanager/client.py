import asyncio
import websockets
import json
import time
import queue
import pandas as pd
from typing import Dict, Any, Union, Tuple, Set
from satorilib.logging import INFO, setup, debug, info, warning, error
from satorilib.datamanager.helper import Identity
from satorilib.datamanager.helper import Message, ConnectedPeer, Subscription
from satorilib.datamanager.api import DataServerApi



class DataClient:

    def __init__(self, serverHost: str, identity: Identity = None):
        self.serverPort = 24602
        self.identity = identity
        self.serverHostPort: Tuple[str, int] = serverHost, self.serverPort
        self.peers: Dict[Tuple[str, int], ConnectedPeer] = {}
        self.subscriptions: dict[Subscription, queue.Queue] = {}
        self.publications: dict[str, str] = {} # {subUuid, publicationUuid}
        self.responses: dict[str, Message] = {}
        self.running = False

    def isConnected(
        self,
        host: Union[str, None] = None,
        port: Union[int, None] = None
    )-> bool:
        host = host or self.serverHostPort[0]
        port = port or self.serverPort
        peer = self.peers.get((host, port))
        if peer is None:
            return False
        if peer.websocket is None or peer.websocket.closed:
            return False
        if peer.listener is None or peer.listener.done():
            return False
        if peer.stop.is_set():
            return False
        return True
        # return self.peers.get((host, port)) is not None

    async def connectToPeer(self, peerHost: str, peerPort: int = 24602):
        '''Connect to other Peers'''
        uri = f'ws://{peerHost}:{peerPort}'
        try:
            websocket = await websockets.connect(uri)
            self.peers[(peerHost, peerPort)] = ConnectedPeer(
                (peerHost, peerPort), websocket
            )
            self.peers[(peerHost, peerPort)].listener = asyncio.create_task(
                self.listenToPeer(self.peers[(peerHost, peerPort)])
            )
            debug(f'Connected to peer at {uri}', print=True)
        except Exception as e:
            # error(f'Failed to connect to peer at {uri}: {e}')
            pass

    async def listenToPeer(self, peer: ConnectedPeer):
        ''' Handles receiving messages from an individual peer '''
        try:
            while True:
                message = Message.fromBytes(await peer.websocket.recv())
                asyncio.create_task(self.handlePeerMessage(message, peer))  # Process async
        # except websockets.exceptions.ConnectionClosed:
        #     self.disconnect(peer)
        except Exception as e:
            error(f"Unexpected error in listenToPeer: {e}")
            await self.disconnect(peer)

    async def handlePeerMessage(self, message: Message, peer: ConnectedPeer) -> None:
        ''' pass to server, modify owner's state, modify self state '''
        await self.handleMessageForOwner(message, peer)
        await self.handleMessageForSelf(message)

    async def handleMessageForServer(self, message: Message) -> None:
        ''' update server about subscription or if the stream is inactive, so it can notify other subscribers '''
        try:
            response = await self.insertStreamData(
                uuid=message.uuid,
                data=message.data,
                isSub=True
            )
            if response.status != DataServerApi.statusSuccess:
                raise Exception(response.senderMsg)
        except Exception as e:
            error('Unable to set data in server: ', e)

    async def handleMessageForOwner(self, message: Message, peer: ConnectedPeer) -> None:
        ''' update state for the calling client '''
        if message.isSubscription:
            if peer.hostPort != self.serverHostPort:
                await self.handleMessageForServer(message) # TODO : for remote subscriptions enable otherwise we skip this
            subscription = self._findSubscription(
                subscription=Subscription(message.uuid)
            )
            q = self.subscriptions.get(subscription)
            if isinstance(q, queue.Queue):
                q.put(message)
            await subscription(message)
        elif message.isResponse:
            self.responses[message.id] = message

    async def handleMessageForSelf(self, message: Message) -> None:
        ''' modify self state '''
        if message.status == 'inactive':
            subscription = self._findSubscription(
                subscription=Subscription(message.uuid))
            if self.subscriptions.get(subscription) is not None:
                del self.subscriptions[subscription]
            if self.publications.get(message.uuid) is not None:
                del self.publications[message.uuid]

    def _findSubscription(self, subscription: Subscription) -> Subscription:
        for s in self.subscriptions.keys():
            if s == subscription:
                return s
        return subscription

    async def listenForResponse(self, callId: Union[str, None] = None) -> Union[dict, None]:
        then = time.time()
        while time.time() < then + 30:
            response = self.responses.get(callId)
            if response is not None:
                del self.responses[callId]
                self.cleanUpResponses()
                return response
            await asyncio.sleep(0.1)
        return None

    def cleanUpResponses(self):
        ''' clear all stale responses since the key is a stringed time.time() '''
        currentTime = time.time()
        stale = 30
        keysToDelete = []
        for key in self.responses.keys():
            try:
                if float(key) < currentTime - stale:
                    keysToDelete.append(key)
            except Exception as e:
                warning(f'error in cleanUpResponses {e}')
        for key in keysToDelete:
            del self.responses[key]

    async def disconnect(self, peer: ConnectedPeer) -> None:
        peer.stop.set()
        await peer.websocket.close()
        del self.peers[peer.hostPort]

    async def disconnectAll(self):
        ''' Disconnect from all peers and stop the server '''
        for connectedPeer in self.peers.values():
            await self.disconnect(connectedPeer)
        info('Disconnected from all peers and stopped server')

    async def connect(self, peerAddr: Tuple[str, int]) -> Dict:
        if peerAddr not in self.peers:
            peerHost, peerPort = peerAddr
            await self.connectToPeer(peerHost, peerPort)

    async def send(
        self,
        peerAddr: Tuple[str, int],
        request: Message,
        sendOnly: bool = False,
    ) -> Message:
        '''Send a request to a specific peer'''
        peerAddr = peerAddr or self.serverHostPort
        await self.connect(peerAddr)
        try:
            await self.peers[peerAddr].websocket.send(request.toBytes())
            if sendOnly:
                return None
            response = await self.listenForResponse(request.id)
            return response
        except Exception as e:
            # error(f'Error sending request to peer: {e}')
            return {'status': 'error', 'message': str(e)}

    async def subscribe(
        self,
        peerHost: str,
        uuid: str,
        publicationUuid: Union[str, None] = None,
        callback: Union[callable, None] = None) -> Message:
        ''' sends a subscription request to external source to recieve subscription updates '''
        if publicationUuid is not None:
            self.publications[uuid] = publicationUuid
        self._addStreamToServer(uuid, publicationUuid)
        subscription = Subscription(uuid, callback)
        self.subscriptions[subscription] = queue.Queue()
        return await self.send((peerHost, self.serverPort), Message(DataServerApi.subscribe.createRequest(uuid))) # should we set isSub as True?

    async def insertStreamData(self, uuid: str, data: pd.DataFrame, replace: bool = False, isSub: bool = False) -> Message:
        ''' sends the observation/prediction data to the server '''
        return await self.send((self.serverHostPort), Message(DataServerApi.insertStreamData.createRequest(uuid, data, replace, isSub=isSub)))

    async def authenticate(self, peerHost: Union[str, None] = None) -> Message:
        ''' client initiates the auth process '''
        auth = self.identity.authenticationPayload(challengeId=peerHost)
        response = await self.send(
            peerAddr=(peerHost, self.serverPort) if peerHost else None,
            request=Message(DataServerApi.initAuthenticate.createRequest(auth=auth)))
        verified = self.idenity.verify(
            msg=self.identity.challenges.get((peerHost, self.serverPort) if peerHost else self.serverHostPort, ''),
            sig=response.auth.get('signature', b''),
            pubkey=response.auth.get('pubkey', None),
            address=response.auth.get('address', None))
        if verified:
            auth = self.identity.authenticationPayload(challenged=response.auth.get('challenge', ''))
            peer = self.peers.get((peerHost, self.serverPort) if peerHost else self.serverHostPort)
            peer.pubkey = response.auth.get('pubkey', None)
            peer.address = response.auth.get('address', None)
            return await self.send(
                peerAddr=(peerHost, self.serverPort) if peerHost else None,
                request=Message(DataServerApi.initAuthenticate.createRequest(auth=auth)))
        await self.disconnect(
            peer=self.peers.get((peerHost, self.serverPort) if peerHost else self.serverHostPort))
        return Message(DataServerApi.statusFail.createResponse("Failed to authenticate"))

    async def isLocalNeuronClient(self) -> Message:
        ''' neuron client tells the server that it is its own neuron client ( authentication done on the client side ) '''
        return await self.send((self.serverHostPort), Message(DataServerApi.isLocalNeuronClient.createRequest()))

    async def isLocalEngineClient(self) -> Message:
        ''' engine client tells the server that it is its own engine client ( authentication done on the client side ) '''
        return await self.send((self.serverHostPort), Message(DataServerApi.isLocalEngineClient.createRequest()))

    async def setPubsubMap(self, uuid: dict) -> Message:
        ''' neuron local client gives the server pub/sub mapping info '''
        return await self.send((self.serverHostPort), Message(DataServerApi.setPubsubMap.createRequest(uuid)))

    async def getPubsubMap(self, peerHost: str = None) -> Message:
        ''' engine local client gets pub/sub mapping info from the server '''
        return await self.send((peerHost, self.serverPort) if peerHost else None, Message(DataServerApi.getPubsubMap.createRequest()))

    async def isStreamActive(self, peerHost: str, uuid: str) -> Message:
        ''' checks if the source server has an active stream the client is trying to subscribe to '''
        return await self.send((peerHost, self.serverPort), Message(DataServerApi.isStreamActive.createRequest(uuid)))

    async def streamInactive(self, uuid: str) -> Message:
        ''' tells the server that a particular stream is not active anymore '''
        return await self.send((self.serverHostPort), Message(DataServerApi.streamInactive.createRequest(uuid)))

    async def getRemoteStreamData(self, peerHost: str, uuid: str)  -> Message:
        ''' request for data from external server '''
        return await self.send((peerHost, self.serverPort), Message(DataServerApi.getStreamData.createRequest(uuid)))

    async def getLocalStreamData(self, uuid: str)  -> Message:
        ''' request for data from local server '''
        return await self.send((self.serverHostPort), Message(DataServerApi.getStreamData.createRequest(uuid)))

    async def getAvailableSubscriptions(self, peerHost: str)  -> Message:
        ''' get from external server its list of available subscriptions '''
        return await self.send((peerHost, self.serverPort), Message(DataServerApi.getAvailableSubscriptions.createRequest()))

    async def addActiveStream(self, uuid: str)  -> Message:
        ''' After confirming a stream is active, its send to its own server for adding it to its available streams '''
        return await self.send((self.serverHostPort), Message(DataServerApi.addActiveStream.createRequest(uuid)))

    async def getStreamDataByRange(self, peerHost: str, uuid: str, fromDate: str, toDate: str)  -> Message:
        ''' request for data thats in a specific timestamp range  '''
        return await self.send((peerHost, self.serverPort), Message(DataServerApi.getStreamDataByRange.createRequest(uuid, fromDate=fromDate, toDate=toDate)))

    async def getStreamObservationByTime(self, peerHost: str, uuid: str, toDate: str)  -> Message:
        ''' request for row equal to or before a timestamp  '''
        return await self.send((peerHost, self.serverPort), Message(DataServerApi.getStreamObservationByTime.createRequest(uuid, toDate=toDate)))

    async def deleteStreamData(self, uuid: str, data: pd.DataFrame)  -> Message:
        ''' request to delete data from its own server '''
        return await self.send((self.serverHostPort), Message(DataServerApi.deleteStreamData.createRequest(uuid, data)))

    async def _addStreamToServer(self, subUuid: str, pubUuid: Union[str, None] = None) -> None:
        ''' Updates server's available streams with local client's subscriptions and predictions streams '''
        try:
            await self.addActiveStream(uuid=subUuid)
        except Exception as e:
            error("Unable to send request to server : ", e)
        if pubUuid is not None:
            try:
                await self.addActiveStream(uuid=pubUuid)
            except Exception as e:
                error("Unable to send request to server : ", e)
