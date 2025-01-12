import asyncio
import websockets
import json
import queue
import pandas as pd
from typing import Dict, Any, Optional, Union, Tuple, Set
from io import StringIO
from satorilib.logging import INFO, setup, debug, info, warning, error
from satorilib.sqlite import SqliteDatabase
from satorilib.utils import generateUUID
from satorilib.data.datamanager.helper import Message, ConnectedPeer, Subscription


class DataServer:
    def __init__(
        self,
        host: str,
        port: int,
        db_path: str = "../data",
        db_name: str = "data.db",
    ):

        self.host = host
        self.port = port
        self.server = None
        self.connectedClients: Dict[Tuple[str, int], ConnectedPeer] = {}
        self.subscriptions: dict[Subscription, queue.Queue] = {}
        self.responses: dict[str, dict] = {}
        self.db = SqliteDatabase(db_path, db_name)
        self.db.importFromDataFolder()  # can be disabled if new rows are added to the Database and new rows recieved are inside the database

    async def start_server(self):
        """Start the WebSocket server"""
        self.server = await websockets.serve(
            self.handleConnection, self.host, self.port
        )
        print(f"Server started on ws://{self.host}:{self.port}")

    async def handleConnection(self, websocket: websockets.WebSocketServerProtocol):
        """Handle incoming connections and messages"""
        peerAddr: Tuple[str, int] = websocket.remote_address
        debug(f"New connection from {peerAddr}")
        self.connectedClients[peerAddr] = self.connectedClients.get(peerAddr, ConnectedPeer(peerAddr, websocket))
        debug("Connected peers:", self.connectedClients)
        try:
            async for message in websocket:
                debug(f"Received request: {message}", print=True)
                try:
                    response = await self.handleRequest(peerAddr, websocket, message)
                    await self.connectedClients[peerAddr].websocket.send(
                        json.dumps(response)
                    )
                except json.JSONDecodeError:
                    await websocket.send(
                        json.dumps(
                            {"status": "error", "message": "Invalid JSON format"}
                        )
                    )
                except Exception as e:
                    await websocket.send(
                        json.dumps(
                            {
                                "status": "error",
                                "message": f"Error processing request: {str(e)}",
                            }
                        )
                    )
        except websockets.exceptions.ConnectionClosed:
            error(f"Connection closed with {peerAddr}")
        finally:
            for key, cp in list(self.connectedClients.items()):
                if cp.websocket == websocket:
                    del self.connectedClients[key]

    async def notifySubscribers(self, msg: Message):
        '''
        is this message something anyone has subscribed to?
        if yes, await self.connected_peers[subscribig_peer].websocket.send(message)
        '''
        for peerAddr in self.connectedClients.values():
           if msg.table_uuid in self.connectedClients[peerAddr].subscriptions:
               await self.connectedClients[peerAddr].websocket.send(msg.to_json())

    async def disconnectAllPeers(self):
        """Disconnect from all peers and stop the server"""
        for connectedPeer in self.connectedClients.values():
            await connectedPeer.websocket.close()
        self.connectedClients.clear()
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        info("Disconnected from all peers and stopped server")

    
    async def handleRequest(
        self,
        peerAddr: Tuple[str, int],
        websocket: websockets.WebSocketServerProtocol,
        message: str,
    ) -> Dict:
        request: Message = Message(json.loads(message))
        # TODO: need an endpoint to notify subscribers
        # neuron-dataClient, raw data -> dataClient --ws-> datamanager.dataServer
        #self.notifySubscribers(request)

        # func(status, id, msg) -> dict{}
        def _create_response( status: str, message: str, data: Optional[str] = None) -> Dict:
            response = {
                "status": status,
                "id": request.id,
                "method":request.method,
                "message": message,
                "params": {
                "table_uuid": request.table_uuid,
                },
                "sub": request.sub if hasattr(request, 'sub') else False
            }
            if data is not None:
                response["data"] = data
            return response
        if request.isSubscription and request.table_uuid is not None:
            self.connectedClients[peerAddr].add_subcription(request.table_uuid)
            return _create_response("success", f"Subscribed to {request.table_uuid}")
        
        elif request.method == 'initiate-connection':
            return _create_response("success", "Connection established")

        if request.table_uuid is None:
            return _create_response("error", "Missing table_uuid parameter")

        if request.method == 'stream_data':
            df = await self._getStreamData(request.table_uuid)
            if df is None:
                return _create_response("error", f"No data found for stream {request.table_uuid}")
            return _create_response("success", f" data found for stream {request.table_uuid}", df.to_json(orient='split')) 

        elif request.method == 'data-in-range':
            if not request.fromDate or not request.toDate:
                return _create_response("error", "Missing from_date or to_date parameter")  
            
            df = await self._getStreamDataByDateRange(
                request.table_uuid, request.fromDate, request.toDate
            )
            if df is None:
                return _create_response("error", f"No data found for stream {request.table_uuid} in specified date range")

            if 'ts' in df.columns:
                df['ts'] = df['ts'].astype(str)
            return _create_response("success", f" data found for stream {request.table_uuid} in specified date range",df.to_json(orient='split'))

        elif request.method == 'record-at-or-before':
            try:
                if request.data is None:
                    return _create_response("error", "No timestamp data provided")
                timestamp_df = pd.read_json(StringIO(request.data), orient='split')
                timestamp = timestamp_df['ts'].iloc[0]
                df = await self._getLastRecordBeforeTimestamp(
                    request.table_uuid, timestamp
                )
                if df is None:
                    return _create_response("error", f"No records found before timestamp for stream {request.table_uuid}")

                if 'ts' in df.columns:
                    df['ts'] = df['ts'].astype(str)
                return _create_response("success", f" records found before timestamp for stream {request.table_uuid}",df.to_json(orient='split'))
            except Exception as e:
                return _create_response("error", f"Error processing timestamp request: {str(e)}") 

        elif request.method == 'insert':
            try:
                if request.data is None:
                    return _create_response("error", "No data provided for insert operation")
                data = pd.read_json(StringIO(request.data), orient='split')
                if request.replace:
                    self.db.deleteTable(request.table_uuid)
                    self.db.createTable(request.table_uuid)
                success = self.db._dataframeToDatabase(request.table_uuid, data)
                updated_df = await self._getStreamData(request.table_uuid)
                return _create_response("success" if success else "error", (
                        f"Data {'replaced' if request.replace else 'merged'} successfully"
                        if success
                        else "Failed to insert data"
                    ))
            except Exception as e:
                return _create_response("error", f"Error inserting data: {str(e)}")
            
        elif request.method == 'delete':
            try:
                if request.data is not None:
                    data = pd.read_json(StringIO(request.data), orient='split')
                    timestamps = data['ts'].tolist()
                    for ts in timestamps:
                        self.db.editTable('delete', request.table_uuid, timestamp=ts)
                    return _create_response("success", "Delete operation completed")
                else:
                    self.db.deleteTable(request.table_uuid)
                    return _create_response("success", f"Table {request.table_uuid} deleted")
            except Exception as e:
                return _create_response("error", f"Error deleting data: {str(e)}")
        else:
            return _create_response("error", f"Unknown request type: {request.method}")
    

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



async def main():
    peer1 = DataServer("0.0.0.0", 8080)
    await peer1.start_server()
    await asyncio.Future()  

if __name__ == "__main__":
    asyncio.run(main())
