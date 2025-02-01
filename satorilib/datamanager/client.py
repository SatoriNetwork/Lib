import asyncio
import websockets
import json
import time
import queue
import pandas as pd
from typing import Dict, Any, Union, Tuple, Set
from satorilib.logging import INFO, setup, debug, info, warning, error
from satorilib.datamanager.helper import Message, ConnectedPeer, Subscription
from satorilib.datamanager.api import DataServerApi

class DataClient:

    def __init__(self, serverHost: str):
        self.serverPort = 24602
        self.serverHostPort: Tuple[str, int] = serverHost, self.serverPort
        self.peers: Dict[Tuple[str, int], ConnectedPeer] = {}
        self.subscriptions: dict[Subscription, queue.Queue] = {}
        self.publications: dict[str, str] = {} # {subUuid, publicationUuid}
        self.responses: dict[str, Message] = {}

    async def connectToPeer(self, peerHost: str, peerPort: int = 24602):
        '''Connect to other Peers'''
        uri = f'ws://{peerHost}:{peerPort}'
        try:
            websocket = await websockets.connect(uri)
            self.peers[(peerHost, peerPort)] = ConnectedPeer(
                (peerHost, peerPort), websocket
            )
            asyncio.create_task(
                self.listenToPeer(self.peers[(peerHost, peerPort)])
            )
            debug(f'Connected to peer at {uri}', print=True)
        except Exception as e:
            error(f'Failed to connect to peer at {uri}: {e}')
    
    async def listenToPeer(self, peer: ConnectedPeer):
        ''' Handles receiving messages from a individual peer '''
        try:
            async for raw_msg in peer.websocket:
                message = Message(json.loads(raw_msg))
                asyncio.create_task(self.handlePeerMessage(message))
        except websockets.exceptions.ConnectionClosed:
            self.disconnect(peer)

    async def handlePeerMessage(self, message: Message) -> None:
        ''' pass to server, modify owner's state, modify self state '''
        await self.handleMessageForOwner(message)
        await self.handleMessageForSelf(message)

    async def handleMessageForServer(self, message: Message) -> None:
        ''' update server about subscription or if the stream is inactive, so it can notify other subscribers '''
        try:
            await self.sendRequest(self.serverHostPort, rawMsg=message) # TODO : fix?
        except Exception as e:
            error('Error sending message to server : ', e)
        
    async def handleMessageForOwner(self, message: Message) -> None:
        ''' update state for the calling client '''
        if message.isSubscription:
            await self.handleMessageForServer(message)
            subscription = self._findSubscription(
                subscription=Subscription(message.method, message.uuid)
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
            self.disconnect(connectedPeer)
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
            await self.peers[peerAddr].websocket.send(request.to_json())
            if sendOnly:
                return None
            response = await self.listenForResponse(request.id)
            return response
        except Exception as e:
            error(f'Error sending request to peer: {e}')
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
        subscription = Subscription(uuid, callback=callback)
        self.subscriptions[subscription] = queue.Queue()
        return await self.send((peerHost, self.serverPort), Message(DataServerApi.subscribe.createRequest(uuid))) # should we set isSub as True?
    
    async def insertStreamData(self, uuid: str, data: pd.DataFrame) -> Message:
        ''' sends the observation/prediction data to the server '''
        return await self.send((self.serverHostPort), Message(DataServerApi.insertStreamData.createRequest(uuid, data)))

    async def isLocalNeuronClient(self) -> Message:
        ''' neuron client tells the server that it is its own neuron client ( authentication done on the client side ) '''
        return await self.send((self.serverHostPort), Message(DataServerApi.isLocalNeuronClient.createRequest()))

    async def isLocalEngineClient(self) -> Message:
        ''' engine client tells the server that it is its own engine client ( authentication done on the client side ) '''
        return await self.send((self.serverHostPort), Message(DataServerApi.isLocalEngineClient.createRequest()))

    async def setPubsubMap(self, uuid: dict) -> Message:
        ''' neuron local client gives the server pub/sub mapping info '''
        return await self.send((self.serverHostPort), Message(DataServerApi.setPubsubMap.createRequest(uuid)))

    async def getPubsubMap(self, peerHost) -> Message:
        ''' engine local client gets pub/sub mapping info from the server '''
        return await self.send((peerHost, self.serverPort), Message(DataServerApi.getPubsubMap.createRequest()))

    async def isStreamActive(self, peerHost: str, uuid: str) -> Message:
        ''' checks if the source server has an active stream the client is trying to subscribe to '''
        return await self.send((peerHost, self.serverPort), Message(DataServerApi.isStreamActive.createRequest(uuid)))

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

    async def getStreamDataByRange(self, peerHost: str, uuid: str)  -> Message:
        ''' request for data thats in a specific timestamp range  '''
        return await self.send((peerHost, self.serverPort), Message(DataServerApi.getStreamDataByRange.createRequest(uuid)))

    async def getStreamObservationByTime(self, peerHost: str, uuid: str)  -> Message:
        ''' request for row equal to or before a timestamp  '''
        return await self.send((peerHost, self.serverPort), Message(DataServerApi.getStreamObservationByTime.createRequest(uuid)))

    async def deleteStreamData(self, uuid: str)  -> Message:
        ''' request to delete data from its own server '''
        return await self.send((self.serverHostPort), Message(DataServerApi.deleteStreamData.createRequest(uuid)))

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


# TODO : clean after confirmation
    # async def sendRequest( 
    #     self,
    #     peerHost: str,
    #     peerPort: int = 24602,
    #     uuid: str = None,
    #     method: str = 'initiate-connection',
    #     isSub: bool = False,
    #     data: pd.DataFrame = None,
    #     replace: bool = False,
    #     fromDate: str = None,
    #     toDate: str = None,
    #     rawMsg: Message = None,
    # ) -> Message:

    #     id = self._generateCallId()

    #     if method == 'data-in-range' and data is not None:
    #         if 'from_ts' in data.columns and 'to_ts' in data.columns:
    #             fromDate = data['from_ts'].iloc[0]
    #             toDate = data['to_ts'].iloc[0]
    #         else:
    #             raise ValueError(
    #                 'DataFrame must contain "from_ts" and "to_ts" columns for date range queries'
    #             )
    #     elif method == 'record-at-or-before':
    #         if data is None:
    #             raise ValueError(
    #                 'DataFrame with timestamp is required for last record before requests'
    #             )
    #         elif 'ts' not in data.columns:
    #             raise ValueError(
    #                 'DataFrame must contain "ts" column for last record before requests'
    #             )

    #     if data is not None:
    #         data = data.to_json(orient='split')

    #     if rawMsg is None:
    #         request = Message(
    #             {
    #                 'method': method,
    #                 'id': id,
    #                 'sub': isSub,
    #                 'params': {
    #                     'uuid': uuid,
    #                     'replace': replace,
    #                     'from_ts': fromDate,
    #                     'to_ts': toDate,
    #                 },
    #                 'data': data,
    #             }
    #         )
    #     else:
    #         request = rawMsg

    #     return await self.send((peerHost, peerPort), request)


    # Note : in-case we need a separate a listener for the internal data server
    # async def connectToServer(self):
    #     '''Connects to our own Server'''
    #     uri = f'ws://{self.serverHostPort}:{24602}'
    #     try:
    #         self.serverWs = await websockets.connect(uri)
    #         asyncio.create_task(self.listenToServer())
    #         debug(f'Connected to Server at {uri}', print=True)
    #     except Exception as e:
    #         error(f'Failed to connect to peer at {uri}: {e}')
            
    # async def listenToServer(self):
    #     ''' listens to our own server '''
    #     try:
    #         async for raw_msg in self.serverWs:
    #             message = Message(json.loads(raw_msg))
    #             asyncio.create_task(self.handleServerMessage(message))
    #     except websockets.exceptions.ConnectionClosed:
    #         self.disconnectServer()

    # async def disconnectServer(self) -> None:
    #     await self.serverWs.close()


    # handleMessageForServer()
        # NOTES
        # dc holds a list of subscriptions (active)
        # ds should just keep an up-to-date copy of that list (should it though? shouldn't we just have one source of truth?)
        #   - n dc has a list of streams it subscribes to (like engine predictions) and it publishes (relays from the real world)
        #   - engine dc has a list of streams it subscribe to and publishes
        #   - 4 list of active streams: n s variable, n publish variable, e s variable, e publish variable
            # this should probably change
            # we want to pass the message to the server for two purposes
            #  - so it can notify it's subscribers
            #  - and also so it can save the data properly
            # so we should just pass it and let it handle it.
                    # look at the message - see if it's special (like 'stream no longer active')
        # if stream no longer active, remove the subscription from the list (that involves telling the server we have removed it)