import asyncio
import websockets
import json
import time
import queue
import pandas as pd
from typing import Dict, Any, Optional, Union, Tuple, Set
from io import StringIO
from satorilib.logging import INFO, setup, debug, info, warning, error
from satorilib.datamanager.server import DataServer
from satorilib.datamanager.helper import Message, ConnectedPeer, Subscription

class DataClient:
    def __init__(
        self,
        server: Union[DataServer, None] = None,
    ):
        self.server = server
        self.peers: Dict[Tuple[str, int], ConnectedPeer] = {}
        self.subscriptions: dict[Subscription, queue.Queue] = {}
        self.responses: dict[str, Message] = {}

    async def connectToServer(self, peerHost: str, peerPort: int = 24602):
        """Connect to our own Server"""
        uri = f"ws://{peerHost}:{peerPort}"
        try:
            websocket = await websockets.connect(uri)
            self.peers[(peerHost, peerPort)] = ConnectedPeer(
                (peerHost, peerPort), websocket
            )
            asyncio.create_task(
                self.listenToPeer(self.peers[(peerHost, peerPort)])
            )
            debug(f"Connected to peer at {uri}", print=True)
        except Exception as e:
            error(f"Failed to connect to peer at {uri}: {e}")

    async def listenToPeer(self, peer: ConnectedPeer):
        """Listen for messages from a connected peer"""

        def handleMultipleMessages(buffer: str):
            '''split on the first newline to handle multiple messages'''
            return buffer.partition('\n')

        async def listen():
            try:
                response = Message(json.loads(await peer.websocket.recv()))
                # could we leverage async here to handle the message in the 
                # background, allowing us to immedaitely return to listening 
                # for the next message?
                self.handleMessage(response)
            except websockets.exceptions.ConnectionClosed:
                self.disconnect(peer)

        while not peer.stop.is_set():
            await listen()

    def findSubscription(self, subscription: Subscription) -> Subscription:
        for s in self.subscriptions.keys():
            if s == subscription:
                return s
        return subscription

    @staticmethod
    def _generateCallId() -> str:
        return str(time.time())

    def handleMessage(self, message: Message) -> None:
        if message.isSubscription:
            if self.server is not None:
                # this should probably change
                # we want to pass the message to the server for two purposes
                #  - so it can notify it's subscribers
                #  - and also so it can save the data properly
                # so we should just pass it and let it handle it.
                self.server.notifySubscribers(message)
            subscription = self.findSubscription(
                subscription=Subscription(message.method, message.table_uuid)
            )
            if message.data is not None:
                try:
                    # how to turn the message into a dataframe
                    #df = pd.read_json(StringIO(message.data), orient='split')
                    # TODO : send observation to server to save in database
                    debug(f"Received and send subscription data to Data Manager for {message.table_uuid}")
                except Exception as e:
                    error(f"Error processing subscription data: {e}")
            q = self.subscriptions.get(subscription)
            if isinstance(q, queue.Queue):
                q.put(message)
            subscription(message)
            debug("Current subscriptions:", self.subscriptions)
            info("Subscribed to : ", message.table_uuid)
        elif message.isResponse:
            self.responses[message.id] = message

    def listenForSubscriptions(self, method: str, params: list) -> dict:
        return self.subscriptions[Subscription(method, params)].get()

    async def listenForResponse(
        self, callId: Union[str, None] = None
    ) -> Union[dict, None]:
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
        '''
        clear all stale responses since the key is a stringed time.time()
        '''
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
        del peer

    async def disconnectAll(self):
        """Disconnect from all peers and stop the server"""
        for connectedPeer in self.peers.values():
            self.disconnect(connectedPeer)
        info("Disconnected from all peers and stopped server")

    async def connect(self, peerAddr: Tuple[str, int]) -> Dict:
        if peerAddr not in self.peers:
            peerHost, peerPort = peerAddr
            await self.connectToServer(peerHost, peerPort)

    async def send(
        self,
        peerAddr: Tuple[str, int],
        request: Message,
        sendOnly: bool = False,
    ) -> Dict:
        """Send a request to a specific peer"""

        await self.connect(peerAddr)
        try:
            await self.peers[peerAddr].websocket.send(request.to_json())
            if sendOnly:
                return None
            response = await self.listenForResponse(request.id)
            return response
        except Exception as e:
            error(f"Error sending request to peer: {e}")
            return {"status": "error", "message": str(e)}

    # should we need this?
    # def resubscribe(self):
    #    if self.connected():
    #        for subscription in self.subscriptions.keys():
    #            self.subscribe(subscription.method, *subscription.params)

    async def subscribe(
        self,
        peerAddr: Tuple[str, int],
        table_uuid: str,
        method: str = "subscribe",
        callback: Union[callable, None] = None,
        data: pd.DataFrame = None,
        replace: bool = False,
        fromDate: str = None,
        toDate: str = None,
    ) -> Dict:
        """
        Creates a subscription request
        """
        id = self._generateCallId()
        subscription = Subscription(method, table_uuid, callback=callback)
        self.subscriptions[subscription] = queue.Queue()
        request = Message(
            {
                "method": method,
                "id": id,
                "sub": False,
                "params": {
                    "table_uuid": table_uuid,
                    "replace": replace,
                    "from_ts": fromDate,
                    "to_ts": toDate,
                },
                "data": data,
            }
        )
        return await self.send(peerAddr, request)

    async def sendRequest( 
        self,
        peerHost: str = '0.0.0.0',
        peerPort: int = 24602,
        table_uuid: str = None,
        method: str = "initiate-connection",
        data: pd.DataFrame = None,
        replace: bool = False,
        fromDate: str = None,
        toDate: str = None,
    ) -> Dict:

        id = self._generateCallId()

        if method == "data-in-range" and data is not None:
            if 'from_ts' in data.columns and 'to_ts' in data.columns:
                fromDate = data['from_ts'].iloc[0]
                toDate = data['to_ts'].iloc[0]
            else:
                raise ValueError(
                    "DataFrame must contain 'from_ts' and 'to_ts' columns for date range queries"
                )
        elif method == "record-at-or-before":
            if data is None:
                raise ValueError(
                    "DataFrame with timestamp is required for last record before requests"
                )
            elif 'ts' not in data.columns:
                raise ValueError(
                    "DataFrame must contain 'ts' column for last record before requests"
                )

        if data is not None:
            data = data.to_json(orient='split')

        request = Message(
            {
                "method": method,
                "id": id,
                "params": {
                    "table_uuid": table_uuid,
                    "replace": replace,
                    "from_ts": fromDate,
                    "to_ts": toDate,
                },
                "data": data,
            }
        )
        return await self.send((peerHost, peerPort), request)
