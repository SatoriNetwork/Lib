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
from satorilib.datamanager.api import DataServerApi, DataClientApi



class DataClient:

    def __init__(self, serverHost: str, serverPort: int = 24600, identity: Union[Identity, None] = None):
        self.serverPort = serverPort
        self.identity = identity
        self.serverHostPort: Tuple[str, int] = serverHost, self.serverPort
        self.peers: Dict[Tuple[str, int], ConnectedPeer] = {}
        self.subscriptions: dict[Subscription, queue.Queue] = {}
        self.publications: dict[str, str] = {}
        self.responses: dict[str, Message] = {}
        self.running = False
        self.proactiveSubscribers: Dict[str, Set[Tuple[str, int]]] = {}

    @property
    def server(self)-> ConnectedPeer:
        return self.peers.get(self.serverHostPort)

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

    async def connectToPeer(self, peerHost: str, peerPort: int = 24600) -> bool:
        '''Connect to other Peers'''
        import socket
        try:
            socket.inet_pton(socket.AF_INET6, peerHost)
            is_ipv6 = True
        except (socket.error, OSError):
            is_ipv6 = False
        # if ':' in peerHost and not peerHost.startswith('['):
        if is_ipv6 and not peerHost.startswith('['):
            uri = f'ws://[{peerHost}]:{peerPort}'
        else:
            uri = f'ws://{peerHost}:{peerPort}'
        try:
            websocket = await websockets.connect(uri)
            self.peers[(peerHost, peerPort)] = ConnectedPeer(
                hostPort=(peerHost, peerPort),
                websocket=websocket,
                isServer=(peerHost, peerPort) == self.serverHostPort)
            self.peers[(peerHost, peerPort)].listener = asyncio.create_task(
                self.listenToPeer(self.peers[(peerHost, peerPort)])
            )
            debug(f'Connected to peer at {uri}', print=True)
            return True
        except Exception as e:
            # error(f'Failed to connect to peer at {uri}: {e}')
            return False

    async def listenToPeer(self, peer: ConnectedPeer):
        ''' Handles receiving messages from an individual peer '''
        try:
            while True:
                msg = await peer.websocket.recv()
                if peer.isIncomingEncrypted:
                    msg = self.identity.decrypt(
                        shared=peer.sharedSecret,
                        aesKey=peer.aesKey,
                        blob=msg)
                message = Message.fromBytes(msg)
                asyncio.create_task(self.handlePeerMessage(message, peer))  # Process async
        # except websockets.exceptions.ConnectionClosed:
        #     self.disconnect(peer)
        except Exception as e:
            # error(f"Unexpected error in listenToPeer: {e}")
            await self.disconnect(peer)

    async def handlePeerMessage(self, message: Message, peer: ConnectedPeer) -> None:
        ''' pass to server, modify owner's state, modify self state '''
        await self.handleMessageForOwner(message, peer)
        # await self.handleMessageForSelf(message) # lets say neuron is subscribed to engine, this will make it unsubscribe

    async def handleMessageForServer(self, message: Message) -> None:
        ''' update server about subscription or if the stream is inactive, so it can notify other subscribers '''
        try:
            await self.insertStreamData(
                uuid=message.uuid,
                data=message.data,
                isSub=True
            )
        except Exception as e:
            error('Unable to set data in server: ', e)

    async def handleMessageForSubscriberClients(self, message: Message):
        ''' connect to each peer and send subscription data '''

        if message.uuid not in self.proactiveSubscribers:
            self.proactiveSubscribers[message.uuid] = set()

        async def sendEachPeer(host, port, message):
            peer_tuple = (host, port)
            try:
                is_first_time = peer_tuple not in self.proactiveSubscribers[message.uuid]
                if is_first_time:
                    response = await self.send(
                        peerAddr=(host, port), 
                        request=Message(DataServerApi.addActiveStream.createRequest(message.uuid)),
                        sendOnly=True
                    )
                    if response is not None:
                        raise Exception
                    else:
                        fullDataResponse = await self.getLocalStreamData(message.uuid)
                        insertFullDataDict = {
                            'status': 'success',
                            'sub': False,
                            'params': {
                                'uuid': message.uuid,
                                'replace': True},
                            'method': DataServerApi.insertStreamData.value,
                            'data': fullDataResponse.data
                        }
                        responseFromPeer = await self.send(
                                                peerAddr=(host, port),
                                                request=Message(insertFullDataDict),
                                                sendOnly=True
                                            )
                        if responseFromPeer is None:
                            self.proactiveSubscribers[message.uuid].add(peer_tuple)
                else:
                    debug(f"Sending stream {message.uuid} to {host}:{port} (subsequent time)")
                
                # Send the actual stream data
                response = await self.send(
                    peerAddr=(host, port),
                    request=message,
                    sendOnly=True
                )
                if response is not None:
                    raise Exception

            except Exception as e:
                self.proactiveSubscribers[message.uuid].discard(peer_tuple)
                debug('Unable to send data to external client: ', e, (host, port))
        
        tasks = []
        for hostPort in message.streamInfo:
            if hostPort.count(':') > 1:
                last_colon = hostPort.rindex(':')
                host = hostPort[:last_colon]
                port = hostPort[last_colon + 1:]
            else:
                host, port = hostPort.split(':')
                
            tasks.append(
                sendEachPeer(str(host), int(port), message)
            )

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    

    async def handleMessageForOwner(self, message: Message, peer: ConnectedPeer) -> None:
        ''' update state for the calling client '''
        if message.isSubscription:
            if peer.hostPort != self.serverHostPort:
                # await self.handleMessageForServer(message)
                pass
            elif message.streamInfo is not None:
                await self.handleMessageForSubscriberClients(message)
            subscription = self._findSubscription(
                subscription=Subscription(message.uuid)
            )
            q = self.subscriptions.get(subscription)
            if isinstance(q, queue.Queue):
                q.put(message)
            await subscription(message)
        elif message.isResponse:
            if message.id is not None:
                self.responses[message.id] = message

    async def handleMessageForSelf(self, message: Message) -> None:
        ''' modify self state '''
        if message.status == DataClientApi.streamInactive.value:
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
        if peer.hostPort in self.peers:
            del self.peers[peer.hostPort]

    async def disconnectAll(self):
        ''' Disconnect from all peers and stop the server '''
        for connectedPeer in self.peers.values():
            await self.disconnect(connectedPeer)
        info('Disconnected from all peers and stopped server')

    async def connect(self, peerAddr: Tuple[str, int], auth: bool = True) -> Dict:
        if peerAddr not in self.peers:
            peerHost, peerPort = peerAddr
            if await self.connectToPeer(peerHost, peerPort) and auth:
                await self.authenticate(peerHost=peerHost, peerPort=peerPort)

    async def send(
        self,
        peerAddr: Tuple[str, int],
        request: Message,
        sendOnly: bool = False,
        auth: bool = True,
    ) -> Message:
        '''Send a request to a specific peer'''
        peerAddr = peerAddr or self.serverHostPort
        await self.connect(peerAddr, auth=auth)
        try:
            msg = request.toBytes()
            peer = self.peers[peerAddr]
            if peer.isOutgoingEncrypted:
                msg = self.identity.encrypt(
                    shared=peer.sharedSecret,
                    aesKey=peer.aesKey,
                    msg=msg)
            await peer.websocket.send(msg)
            if sendOnly:
                return None
            response = await self.listenForResponse(request.id)
            return response
        except Exception as e:
            # error(f'Error sending request to peer: {e}')
            return {'status': 'error', 'message': str(e)}

    async def subscribe(
        self,
        uuid: str,
        peerHost: Union[str, None] = None,
        peerPort: Union[int, None] = None,
        publicationUuid: Union[str, None] = None,
        callback: Union[callable, None] = None,
        engineSubscribed: bool = False) -> Message:
        ''' sends a subscription request to recieve subscription updates '''
        if publicationUuid is not None:
            self.publications[uuid] = publicationUuid
        if engineSubscribed is True:
            self._addStreamToServer(uuid, publicationUuid)
        subscription = Subscription(uuid, callback)
        self.subscriptions[subscription] = queue.Queue()
        if peerHost is not None and peerPort is not None:
            peerAddr = (peerHost, peerPort)
            auth = True
        else:
            peerAddr = None
            auth = False
        return await self.send(peerAddr=peerAddr, request=Message(DataServerApi.subscribe.createRequest(uuid)), auth=auth)

    async def authenticate(self, peerHost: Union[str, None] = None, peerPort: Union[int, None] = None, islocal: str = None) -> Message:
        ''' client initiates the auth process '''
        peerHost = peerHost if peerHost is not None else self.serverHostPort[0]
        peerPort = peerPort if peerPort is not None else self.serverPort
        auth = self.identity.authenticationPayload(challengeId=peerHost)
        if islocal is not None:
            auth['islocal'] = islocal
        response = await self.send(
            peerAddr=(peerHost, peerPort),
            request=Message(DataServerApi.initAuthenticate.createRequest(auth=auth)),
            auth=False)
        if response.status == DataServerApi.statusSuccess.value:
            verified = self.identity.verify(
                msg=self.identity.challenges.get(peerHost, ''),
                sig=response.auth.get('signature', b''),
                pubkey=response.auth.get('pubkey', None),
                address=response.auth.get('address', None))
            if verified:
                auth = self.identity.authenticationPayload(challenged=response.auth.get('challenge', ''))
                peer = self.peers.get((peerHost, peerPort), '')
                answer = await self.send(
                    peerAddr=(peerHost, peerPort),
                    request=Message(DataServerApi.initAuthenticate.createRequest(auth=auth)),
                    auth=False)
                if answer.status == DataServerApi.statusSuccess.value:
                    peer.setPubkey(response.auth.get('pubkey', None))
                    peer.setAddress(response.auth.get('address', None))
                    peer.setSharedSecret(self.identity.secret(peer.pubkey))
                    peer.setAesKey(self.identity.derivedKey(peer.sharedSecret))
                    return answer
        await self.disconnect(
            peer=self.peers.get((peerHost, peerPort), ''))
        return Message(DataServerApi.statusFail.createResponse("Failed to authenticate"))

    async def setPubsubMap(self, uuid: dict) -> Message:
        ''' neuron local client gives the server pub/sub mapping info '''
        return await self.send((self.serverHostPort), Message(DataServerApi.setPubsubMap.createRequest(uuid)), auth=False)

    async def getPubsubMap(self, peerHost: Union[str, None] = None, peerPort: Union[int, None] = None) -> Message:
        ''' engine local client gets pub/sub mapping info from the server '''
        if peerHost is not None and peerPort is not None:
                peerAddr = (peerHost, peerPort)
                auth = True
        else:
            peerAddr = None
            auth = False
        return await self.send(
            peerAddr=peerAddr, 
            request=Message(DataServerApi.getPubsubMap.createRequest()), 
            auth=auth
        )

    async def isStreamActive(self, uuid: str, peerHost: Union[str, None] = None, peerPort: Union[int, None] = None) -> Message:
        ''' checks if the source server has an active stream the client is trying to subscribe to '''
        if peerHost is not None and peerPort is not None:
            peerAddr = (peerHost, peerPort)
            auth = True
        else:
            peerAddr = None
            auth = False
        return await self.send(
            peerAddr=peerAddr, 
            request=Message(DataServerApi.isStreamActive.createRequest(uuid)), 
            auth=auth
        )

    async def streamInactive(self, uuid: str) -> Message:
        ''' tells the server that a particular stream is not active anymore '''
        return await self.send((self.serverHostPort), Message(DataServerApi.streamInactive.createRequest(uuid)), auth=False)

    async def insertStreamData(self, uuid: str, data: pd.DataFrame, replace: bool = False, isSub: bool = False, sendOnly: bool = False) -> Message:
        ''' sends the observation/prediction data to the server '''
        return await self.send(peerAddr=(self.serverHostPort), 
                               request=Message(DataServerApi.insertStreamData.createRequest(uuid, data, replace, isSub=isSub)),
                               sendOnly=sendOnly,
                               auth=False)

    async def getRemoteStreamData(self, peerHost: str, uuid: str, peerPort: Union[int, None] = None)  -> Message:
        ''' request for data from external server '''
        return await self.send((peerHost, peerPort if peerPort is not None else self.serverPort), Message(DataServerApi.getStreamData.createRequest(uuid)))

    async def getLocalStreamData(self, uuid: str)  -> Message:
        ''' request for data from local server '''
        return await self.send((self.serverHostPort), Message(DataServerApi.getStreamData.createRequest(uuid)), auth=False)

    async def getAvailableSubscriptions(self, peerHost: str, peerPort: Union[int, None] = None)  -> Message:
        ''' get from external server its list of available subscriptions '''
        return await self.send((peerHost, peerPort if peerPort is not None else self.serverPort), Message(DataServerApi.getAvailableSubscriptions.createRequest()))

    async def addActiveStream(self, uuid: str)  -> Message:
        ''' After confirming a stream is active, its send to its own server for adding it to its available streams '''
        return await self.send((self.serverHostPort), Message(DataServerApi.addActiveStream.createRequest(uuid)), auth=False)

    async def getStreamDataByRange(self, peerHost: str, uuid: str, fromDate: str, toDate: str, peerPort: Union[int, None] = None)  -> Message:
        ''' request for data thats in a specific timestamp range  '''
        return await self.send((peerHost, peerPort if peerPort is not None else self.serverPort), Message(DataServerApi.getStreamDataByRange.createRequest(uuid, fromDate=fromDate, toDate=toDate)))

    async def getStreamObservationByTime(self, peerHost: str, uuid: str, toDate: str, peerPort: Union[int, None] = None)  -> Message:
        ''' request for row equal to or before a timestamp  '''
        return await self.send((peerHost, peerPort if peerPort is not None else self.serverPort), Message(DataServerApi.getStreamObservationByTime.createRequest(uuid, toDate=toDate)))

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
