import asyncio
import websockets
import json
import time
import queue
import pandas as pd
from typing import Dict, Any, Optional, Union, Tuple, Set
from io import StringIO
from satorilib.logging import INFO, setup, debug, info, warning, error
from satorilib.sqlite import SqliteDatabase
from satorilib.utils import generateUUID
from satorilib.data.datamanager.server import DataServer
from satorilib.data.datamanager.helper import Message, ConnectedPeer, Subscription


class DataClient:
    def __init__(
        self,
        host: str = None,
        port: int = None,
        db_path: str = "../../data",
        db_name: str = "data.db",
        server: Union[DataServer, None] = None,
    ):

        self.host = host
        self.port = port
        self.server = server
        self.connectedServers: Dict[Tuple[str, int], ConnectedPeer] = {}
        self.subscriptions: dict[Subscription, queue.Queue] = {}
        self.responses: dict[str, Message] = {}
        self.db = SqliteDatabase(db_path, db_name)

    async def connectToPeer(self, peerHost: str, peerPort: int) -> bool:
        """Connect to another peer"""
        uri = f"ws://{peerHost}:{peerPort}"
        try:
            websocket = await websockets.connect(uri)
            self.connectedServers[(peerHost, peerPort)] = ConnectedPeer(
                (peerHost, peerPort), websocket
            )
            asyncio.create_task(
                self.listenToPeer(self.connectedServers[(peerHost, peerPort)])
            )
            debug(f"Connected to peer at {uri}", print=True)
            return True
        except Exception as e:
            error(f"Failed to connect to peer at {uri}: {e}")
            return False

    async def listenToPeer(self, peer: ConnectedPeer):
        """Listen for messages from a connected peer"""

        def handleMultipleMessages(buffer: str):
            '''split on the first newline to handle multiple messages'''
            return buffer.partition('\n')

        async def listen():
            try:
                response = Message(json.loads(await peer.websocket.recv()))
                await self.handleMessage(response)
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

    async def handleMessage(self, message: Message) -> None:
        if message.isSubscription or (hasattr(message, 'sub') and message.sub):
            if self.server is not None:
                self.server.notifySubscribers(message)
            subscription = self.findSubscription(
                subscription=Subscription(message.method, params=[])
            )
            q = self.subscriptions.get(
                subscription
            )  # when we ask for a subscription we save.
            if isinstance(q, queue.Queue):
                q.put(message)
            subscription(message)
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
            # time.sleep(1)
            await asyncio.sleep(1)
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

    # todo add all
    async def handleResponse(self, response: Message) -> None:
        if response.status == "success" and response.data is not None:
            try:
                df = pd.read_json(StringIO(response.data), orient='split')
                if response.method in ["record-at-or-before", "data-in-range"]:
                    self.db.deleteTable(response.table_uuid)
                    self.db.createTable(response.table_uuid)
                self.db._dataframeToDatabase(response.table_uuid, df)
                info(f"\nData saved to database: {self.db.dbname}")
                debug(f"Table name: {response.table_uuid}")
            except Exception as e:
                error(f"Database error: {e}")

    async def disconnect(self, peer: ConnectedPeer) -> None:
        peer.stop.set()
        await peer.websocket.close()
        del peer

    async def disconnectAll(self):
        """Disconnect from all peers and stop the server"""
        for connectedPeer in self.connectedServers.values():
            self.disconnect(connectedPeer)
        info("Disconnected from all peers and stopped server")

    async def connect(
        self,
        peerAddr: Tuple[str, int],
        request: Message,
    ) -> Dict:
        if peerAddr not in self.connectedServers:
            peerHost, peerPort = peerAddr
            success = await self.connectToPeer(peerHost, peerPort)
            if not success:
                return {
                    "status": "error",
                    "id": request.id,
                    "message": "Failed to connect to peer",
                }

    async def send(
        self,
        peerAddr: Tuple[str, int],
        request: Message,
        sendOnly: bool = False,
    ) -> Dict:
        """Send a request to a specific peer"""

        debug(request.id, print=True)
        await self.connect(peerAddr, request)
        msg = request.to_json()
        try:
            await self.connectedServers[peerAddr].websocket.send(msg)
            if sendOnly:
                return None
            return await self.listenForResponse(request.id)
        except Exception as e:
            error(f"Error sending request to peer: {e}")
            return {"status": "error", "message": str(e)}

    # should we need this?
    # def resubscribe(self):
    #    if self.connected():
    #        for subscription in self.subscriptions.keys():
    #            self.subscribe(subscription.method, *subscription.params)

    # Refactor: could be made to look like sendRequest creating method from passed in details:
    async def subscribe(
        self,
        peerAddr: Tuple[str, int],
        request: Message,
        callback: Union[callable, None] = None,
    ):
        self.subscriptions[
            Subscription(request.method, request.params, callback=callback)
        ] = queue.Queue()
        return await self.send(peerAddr, request)

    async def sendRequest(
        self,
        peerAddr: Tuple[str, int],
        table_uuid: str = None,
        method: str = "initiate-connection",
        sub: bool = False,
        data: pd.DataFrame = None,
        replace: bool = False,
        fromDate: str = None,
        toDate: str = None,
    ) -> Dict:

        # from datetime import datetime
        # idStr: str = str(
        #     generateUUID({'method': method, 'currentTime': datetime.now()})
        # )
        id = self._generateCallId()

        if method == "initiate-connection":
            request = Message({"method": method, "id": id})
        elif method == "data-in-range" and data is not None:
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
            if 'ts' not in data.columns:
                raise ValueError(
                    "DataFrame must contain 'ts' column for last record before requests"
                )

        if data is not None:
            data = data.to_json(orient='split')

        request = Message(
            {
                "method": method,
                "id": id,
                "sub": sub,
                "params": {
                    "table_uuid": table_uuid,
                    "replace": replace,
                    "from_ts": fromDate,
                    "to_ts": toDate,
                },
                "data": data,
            }
        )
        if sub:
            return await self.subscribe(peerAddr, request)
        return await self.send(peerAddr, request)

    async def _getStreamData(self, table_uuid: str) -> pd.DataFrame:
        """Get data for a specific stream directly from SQLite database"""
        try:
            df = self.db._databasetoDataframe(table_uuid)
            if df is None or df.empty:
                debug("No data available to send")
                return pd.DataFrame()
            return df
        except Exception as e:
            error(f"Error getting data for stream {table_uuid}: {e}")

    async def _getStreamDataByDateRange(
        self, table_uuid: str, from_date: str, to_date: str
    ) -> pd.DataFrame:
        """Get stream data within a specific date range (inclusive)"""
        try:
            df = self.db._databasetoDataframe(table_uuid)
            if df is None or df.empty:
                debug("No data available to send")
                return pd.DataFrame()
            from_ts = pd.to_datetime(from_date)
            to_ts = pd.to_datetime(to_date)
            df['ts'] = pd.to_datetime(df['ts'])
            filtered_df = df[(df['ts'] >= from_ts) & (df['ts'] <= to_ts)]
            return filtered_df if not filtered_df.empty else pd.DataFrame()
        except Exception as e:
            error(f"Error getting data for stream {table_uuid} in date range: {e}")

    async def _getLastRecordBeforeTimestamp(
        self, table_uuid: str, timestamp: str
    ) -> pd.DataFrame:
        """Get the last record before the specified timestamp (inclusive)"""
        try:
            df = self.db._databasetoDataframe(table_uuid)
            if df is None or df.empty:
                return pd.DataFrame()
            ts = pd.to_datetime(timestamp)
            df['ts'] = pd.to_datetime(df['ts'])
            if not df.loc[df['ts'] == ts].empty:  # First check for exact match
                return df.loc[df['ts'] == ts]
            before_ts = df.loc[
                df['ts'] < ts
            ]  # check for timestamp before specified timestamp
            return before_ts.iloc[[-1]] if not before_ts.empty else pd.DataFrame()
        except Exception as e:
            error(
                f"Error getting last record before timestamp for stream {table_uuid}: {e}"
            )

