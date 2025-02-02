import asyncio
import websockets
import json
import pandas as pd
from typing import Any, Union
from io import StringIO
from satorilib.logging import INFO, setup, debug, info, warning, error
from satorilib.sqlite import SqliteDatabase
from satorilib.datamanager.helper import Message, Peer, ConnectedPeer
from satorilib.datamanager.api import DataServerApi 
from satorilib.datamanager.api import DataClientApi


class DataServer:
    def __init__(
        self,
        host: str,
        port: int = 24602,
        db_path: str = "../data",
        db_name: str = "data.db",
    ):
        self.host = host
        self.port = port
        self.server = None # TODO : avoid
        self.connectedClients: dict[Peer, ConnectedPeer] = {}
        self.pubSubMapping: dict[str, dict] = {}
        self.db = SqliteDatabase(db_path, db_name)
        self.db.importFromDataFolder()  # can be disabled if new rows are added to the Database and new rows recieved are inside the database

    @property
    def localClients(self) -> dict[Peer, ConnectedPeer]:
        ''' returns dict of clients that have local flag set as True'''
        return {k:v for k,v in self.connectedClients.items() if v.isLocal}

    @property
    def availableStreams(self) -> list[str]:
        ''' returns a list of streams the server publishes or others can subscribe to '''
        return list(set().union(*[v.publications for v in self.localClients.values()]))

    async def startServer(self):
        """ Start the WebSocket server """
        self.server = await websockets.serve(
            self.handleConnection, self.host, self.port
        )

    async def handleConnection(self, websocket: websockets.WebSocketServerProtocol):
        """ handle incoming connections and messages """
        peerAddr: Peer = Peer(*websocket.remote_address) # TODO : see the data structure again
        self.connectedClients[peerAddr] = self.connectedClients.get(
            peerAddr, ConnectedPeer(peerAddr, websocket)
        )
        debug("Connected peers:", self.connectedClients, print=True)
        try:
            async for message in websocket:
                debug(f"Received request: {message}", print=True)
                try:
                    response = await self.handleRequest(peerAddr, message)
                    await self.connectedClients[peerAddr].websocket.send(
                        json.dumps(response)
                    )
                    await asyncio.sleep(5)
                    response = {
                        'method': DataClientApi.streamObservation.value,
                    }
                    await self.connectedClients[peerAddr].websocket.send(
                        json.dumps(response)
                    )
                    await asyncio.sleep(5)
                    response = {
                        'method': DataClientApi.streamObservation.value,
                    }
                    await self.connectedClients[peerAddr].websocket.send(
                        json.dumps(response)
                    )
                    await asyncio.sleep(5)
                    response = {
                        'method': DataClientApi.streamObservation.value,
                    }
                    await self.connectedClients[peerAddr].websocket.send(
                        json.dumps(response)
                    )
                    await asyncio.sleep(5)
                    response = {
                        'method': DataClientApi.streamObservation.value,
                    }
                    await self.connectedClients[peerAddr].websocket.send(
                        json.dumps(response)
                    )
                    await asyncio.sleep(5)
                    response = {
                        'method': DataClientApi.streamObservation.value,
                    }
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
            for key, peer in list(self.connectedClients.items()):
                if peer.websocket == websocket:
                    del self.connectedClients[key]

    async def updateSubscribers(self, msg: Message):
        '''
        is this message something anyone has subscribed to?
        if yes, await self.connected_peers[subscribig_peer].websocket.send(message)
        '''
        for connectedClient in self.connectedClients.values():
            if msg.uuid in connectedClient.subscriptions:
                await connectedClient.websocket.send(msg.to_json())

    async def disconnectAllPeers(self):
        """ disconnect from all peers and stop the server """
        for connectedPeer in self.connectedClients.values():
            await connectedPeer.websocket.close()
        self.connectedClients.clear()
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        info("Disconnected from all peers and stopped server")

    async def handleRequest(
        self,
        peerAddr: Peer,
        message: str,
    ) -> dict:
        ''' incoming requests handled according to the method '''

        request: Message = Message(json.loads(message))
        def _createResponse(
            status: str,
            message: str,
            data: Union[str, None] = None,
            streamInfo: list = None,
            uuid_override: str = None,
        ) -> dict:
            response = {
                "status": status,
                "id": request.id,
                "method": request.method,
                "message": message,
                "params": {
                    "uuid": uuid_override or request.uuid,
                },
                "sub": request.sub,
            }
            if data is not None:
                response["data"] = data
            if streamInfo is not None:
                response["stream_info"] = streamInfo
            return response

        def _convertPeerInfoDict(data: dict, pubsubmap: bool = False) -> dict:
            convertedData = {}
            if pubsubmap:
                for subUuid, data in data.items():
                    convertedData[subUuid] = data
            else:
                for uuid, peerInfo in data.items():
                    convertedData[uuid] = {
                        'subscribers': peerInfo.subscribersIp,
                        'publishers': peerInfo.publishersIp
                    }
            return convertedData

        if request.method == DataServerApi.isLocalNeuronClient.value:
            ''' local neuron client sends this request to server so the server identifies the client as its local client after auth '''
            # local - TODO: add authentication
            self.connectedClients[peerAddr].isNeuron = True
            return DataServerApi.statusSuccess.createResponse('Authenticated as Neuron client', request.id)

        elif request.method == DataServerApi.isLocalEngineClient.value:
            ''' engine client sends this request to server so the server identifies the client as its local client after auth '''
            # local - TODO: add authentication
            self.connectedClients[peerAddr].isEngine = True
            return DataServerApi.statusSuccess.createResponse('Authenticated as Engine client', request.id)

        elif request.method == DataServerApi.setPubsubMap.value:
            ''' local neuron client sends the related pub-sub streams it recieved from the rendevous server '''
            for sub_uuid, data in request.uuid.items():
                self.pubSubMapping[sub_uuid] = data
            return DataServerApi.statusSuccess.createResponse('Pub-Sub map set in Server', request.id)

        elif request.method == DataServerApi.getPubsubMap.value:
            ''' this request fetches related pub-sub streams '''
            streamDict = _convertPeerInfoDict(self.pubSubMapping, True)
            return DataServerApi.statusSuccess.createResponse('Pub-Sub map fetched from server', request.id, streamInfo=streamDict)

        elif request.method == DataServerApi.isStreamActive.value:
            ''' client asks the server whether it has the stream its trying to subscribe to in its publication list  '''
            if request.uuid in self.availableStreams():
                return DataServerApi.statusSuccess.createResponse('Subscription stream available to subscribe to', request.id)
            else:
                return DataServerApi.statusFail.createResponse('Subscription not available', request.id)
        
        elif request.method == DataServerApi.streamInactive.value:
            ''' local client tells the server is not active anymore '''
            publication_uuid = self.pubSubMapping.get(request.uuid, {}).get('publicationUuid')
            if publication_uuid is not None:
                connectedClientsProvidingThisStream = len([request.uuid in localClient.publications for localClient in self.localClients.values()])
                if connectedClientsProvidingThisStream > 1:
                    self.connectedClients[peerAddr].remove_subscription(request.uuid)
                    self.connectedClients[peerAddr].remove_publication(request.uuid)
                    self.connectedClients[peerAddr].remove_subscription(publication_uuid)
                    self.connectedClients[peerAddr].remove_publication(publication_uuid)
                    await self.updateSubscribers(Message(_createResponse("inactive", "Stream inactive")))
                    await self.updateSubscribers(Message(_createResponse("inactive", "Stream inactive", uuid_override=publication_uuid)))
                else:
                    for connectedClient in self.connectedClients.values():
                        connectedClient.remove_subscription(request.uuid)
                        connectedClient.remove_publication(request.uuid)
                        connectedClient.remove_subscription(publication_uuid)
                        connectedClient.remove_publication(publication_uuid)
                    await self.updateSubscribers(Message(_createResponse("inactive", "Stream inactive")))
                    await self.updateSubscribers(Message(_createResponse("inactive", "Stream inactive", uuid_override=publication_uuid)))
                return DataServerApi.statusSuccess.createResponse('inactive stream removed from server', request.id)
            else:
                return DataServerApi.statusFail.createResponse('Requested uuid is not present in the server', request.id)

        elif request.method == DataServerApi.getAvailableSubscriptions.value:
            ''' client asks the server to send its publication list to know which stream it can subscribe to '''
            return DataServerApi.statusSuccess.createResponse('Available streams fetched', request.id, streamInfo=self.availableStreams())

        elif request.method == DataServerApi.subscribe.value:
            ''' client tells the server it wants to subscribe so the server can add to its subscribers '''
            if request.uuid is not None:
                self.connectedClients[peerAddr].add_subscription(request.uuid)
                return DataServerApi.statusSuccess.createResponse('Subscriber info set', request.id)
            return DataServerApi.statusFail.createResponse('UUID must be provided', request.id)

        elif request.method == DataServerApi.addActiveStream.value:
            ''' local client tells the server to add a stream to its publication list since the local client is subscribed to that stream '''
            if request.uuid is not None:
                self.connectedClients[peerAddr].add_publication(request.uuid)
                return DataServerApi.statusSuccess.createResponse('Publication Stream added', request.id)
            return DataServerApi.statusFail.createResponse('UUID must be provided', request.id)

        if request.uuid is None:
            return DataServerApi.statusFail.createResponse('Missing uuid parameter', request.id)

        elif request.method == DataServerApi.getStreamData.value:
            ''' fetches the whole requested dataframe '''
            try:
                df = self._getStreamData(request.uuid)
                if not df.empty:
                    return DataServerApi.statusFail.createResponse('No data found for stream', request.id)
                return DataServerApi.statusSuccess.createResponse('data fetched for the stream', request.id, df.to_json(orient='split') )
            except Exception as e:
                return DataServerApi.statusFail.createResponse('Failed to fetch data', request.id)

        elif request.method == DataServerApi.getStreamDataByRange.value:
            ''' fetches dataframe of a particulare date range '''
            try:
                if not request.fromDate or not request.toDate:
                    return DataServerApi.statusFail.createResponse('Missing from_date or to_date parameter', request.id)
                df = self._getStreamDataByDateRange(
                    request.uuid, request.fromDate, request.toDate
                )
                if not df.empty():
                    return DataServerApi.statusFail.createResponse('No data found for stream in specified timestamp range', request.id)
                if 'ts' in df.columns:
                    df['ts'] = df['ts'].astype(str)
                return DataServerApi.statusSuccess.createResponse('data fetched for stream in specified date range', request.id, df.to_json(orient='split'))
            except Exception as e:
                return DataServerApi.statusFail.createResponse('Failed to fetch data', request.id)

        elif request.method == DataServerApi.getStreamObservationByTime.value:
            ''' fetches a sinlge row as dataframe of the record before or equal to specified timestamp '''
            try:
                if request.data is None:
                    return DataServerApi.statusFail.createResponse('No timestamp data provided', request.id)
                timestamp = pd.read_json(StringIO(request.data), orient='split')['ts'].iloc[0]
                df = self._getLastRecordBeforeTimestamp(
                    request.uuid, timestamp
                )
                if not df.empty():
                    return DataServerApi.statusFail.createResponse('No records found before timestamp for stream', request.id)
                if 'ts' in df.columns:
                    df['ts'] = df['ts'].astype(str)
                return DataServerApi.statusSuccess.createResponse('records found before timestamp for stream', request.id, df.to_json(orient='split'))
            except Exception as e:
                return DataServerApi.statusFail.createResponse('Failed to fetch data', request.id)

        elif request.method == DataServerApi.insertStreamData.value:
            ''' inserts the dataframe send in request into the database '''
            try:
                if request.data is None:
                    return DataServerApi.statusFail.createResponse('No data provided', request.id)
                data = pd.read_json(StringIO(request.data), orient='split')
                if request.replace:
                    self.db.deleteTable(request.uuid)
                    self.db.createTable(request.uuid)
                if request.isSubscription:
                    if request.uuid in self.availableStreams():
                        self.db._addSubDataToDatabase(request.uuid, data)
                        await self.updateSubscribers(request)
                        return DataServerApi.statusSuccess.createResponse('Data added to server database', request.id)
                    else:
                        return DataServerApi.statusFail.createResponse('Subcsription not in server list', request.id)
                else:
                    if self.db._addDataframeToDatabase(request.uuid, data):
                        return DataServerApi.statusSuccess.createResponse('Data added to dataframe', request.id)
            except Exception as e:
                return DataServerApi.statusFail.createResponse('Failed to add data to dataframe', request.id)

        elif request.method == DataServerApi.isStreamActive.value:
            ''' client asks the server whether it has the stream its trying to subscribe to in its publication list  '''
            if request.uuid in self.availableStreams():
                return DataServerApi.statusSuccess.createResponse('Subscription stream available to subscribe to', request.id)
            else:
                return DataServerApi.statusFail.createResponse('Subscription not available', request.id)

        elif request.method == DataServerApi.deleteStreamData.value:
            ''' request to remove data from the database '''
            try:
                if request.data is not None:
                    data = pd.read_json(StringIO(request.data), orient='split')
                    timestamps = data['ts'].tolist()
                    for ts in timestamps:
                        self.db.editTable('delete', request.uuid, timestamp=ts)
                    return DataServerApi.statusSuccess.createResponse('Delete operation completed', request.id)
                # else: # TODO : should we delete the whole table?
                #     self.db.deleteTable(request.uuid)
                #     return DataServerApi.statusSuccess.createResponse('Table {request.uuid} deleted', request.id)
            except Exception as e:
                return DataServerApi.statusFail.createResponse(f'Error deleting data: {str(e)}', request.id)

        return DataServerApi.unknown.createResponse("Unknown request", request.id)

    def _getStreamData(self, uuid: str) -> pd.DataFrame:
        """Get data for a specific stream directly from SQLite database"""
        try:
            df = self.db._databasetoDataframe(uuid)
            if df is None or df.empty:
                debug("No data available to send")
                return pd.DataFrame()
            return df
        except Exception as e:
            error(f"Error getting data for stream {uuid}: {e}")

    def _getStreamDataByDateRange(
        self, uuid: str, from_date: str, to_date: str
    ) -> pd.DataFrame:
        """Get stream data within a specific date range (inclusive)"""
        try:
            df = self.db._databasetoDataframe(uuid)
            if df is None or df.empty:
                debug("No data available to send")
                return pd.DataFrame()
            from_ts = pd.to_datetime(from_date)
            to_ts = pd.to_datetime(to_date)
            df['ts'] = pd.to_datetime(df['ts'])
            filtered_df = df[(df['ts'] >= from_ts) & (df['ts'] <= to_ts)]
            return filtered_df if not filtered_df.empty else pd.DataFrame()
        except Exception as e:
            error(f"Error getting data for stream {uuid} in date range: {e}")

    def _getLastRecordBeforeTimestamp(
        self, uuid: str, timestamp: str
    ) -> pd.DataFrame:
        """Get the last record before the specified timestamp (inclusive)"""
        try:
            df = self.db._databasetoDataframe(uuid)
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
                f"Error getting last record before timestamp for stream {uuid}: {e}"
            )


# TODO : cleanup after confirmation
# old requests :

        # if request.method == 'initiate-server-connection':
        #     ''' local clients first sends this request to server so the server identifies the client as its local client after auth '''
        #     return _createResponse("success", "Connection established")

        
        # elif request.method == 'send-pubsub-map':
        #     ''' local neuron client sends the related pub-sub streams recieved from the rendevous server '''
        #     for sub_uuid, data in request.uuid.items():
        #         self.pubSubMapping[sub_uuid] = data
        #     return _createResponse("success", "Pub-Sub Mapping added in Server")

        
        # elif request.method == 'get-pubsub-map':
        #     ''' engine data client asks the server for pub-sub map streams to identify related pub-sub streams '''
        #     streamDict = _convertPeerInfoDict(self.pubSubMapping, True)
        #     return _createResponse(
        #         "success",
        #         "Stream information of subscriptions with peer information recieved",
        #         streamInfo=streamDict)

        # elif request.method == 'confirm-subscription' and request.uuid is not None:
        #     ''' client asks the server whether it has the stream its trying to subscribe to in its publication list  '''
        #     if request.uuid in self.availableStreams():
        #         return _createResponse("success", "Subscription stream available to subscribe to")
        #     else:
        #         return _createResponse("inactive", "Subscription not available")

                    
        # elif request.method == 'stream-inactive' and request.uuid is not None:
        #     '''
        #     how many connected clients (local) do I have that publish this stream to me?
        #     if < 2 then I should remove the stream from my availableStreams: remove from everyone
        #     else remove from the peer that sent the request
        #     '''
        #     publication_uuid = self.pubSubMapping.get(request.uuid, {}).get('publicationUuid')
        #     if publication_uuid is not None:
        #         connectedClientsProvidingThisStream = len([request.uuid in localClient.publications for localClient in self.localClients.values()])
        #         if connectedClientsProvidingThisStream > 1:
        #             self.connectedClients[peerAddr].remove_subscription(request.uuid)
        #             self.connectedClients[peerAddr].remove_publication(request.uuid)
        #             self.connectedClients[peerAddr].remove_subscription(publication_uuid)
        #             self.connectedClients[peerAddr].remove_publication(publication_uuid)
        #             await self.updateSubscribers(Message(_createResponse("inactive", "Stream inactive")))
        #             await self.updateSubscribers(Message(_createResponse("inactive", "Stream inactive", uuid_override=publication_uuid)))
        #         else:
        #             for connectedClient in self.connectedClients.values():
        #                 connectedClient.remove_subscription(request.uuid)
        #                 connectedClient.remove_publication(request.uuid)
        #                 connectedClient.remove_subscription(publication_uuid)
        #                 connectedClient.remove_publication(publication_uuid)
        #             await self.updateSubscribers(Message(_createResponse("inactive", "Stream inactive")))
        #             await self.updateSubscribers(Message(_createResponse("inactive", "Stream inactive", uuid_override=publication_uuid)))
        #         return _createResponse("success", "Message receieved by the server")
        #     else:
        #         return _createResponse("error", "Requested uuid is not present in the server")
                
        # elif request.method == 'send-available-subscription':
        #     ''' client asks the server to send its publication list to know which stream it can subscribe to '''
        #     return _createResponse("success", "Available streams sent", streamInfo=self.availableStreams())

                
        # elif request.method == 'subscribe' and request.uuid is not None:
        #     '''
        #     from server perspective: 

        #     local ec - subscribes to a stream from some peer
        #     local ec - "add this to the publications that I'm promising to send you, our own server"
            
        #     local server - hangin
        #     remote client - says "what streams can you provide?"
        #     remote client - says "I want to subscribe to this stream that you promised you can provide"

        #     '''
        #     if request.uuid is not None:
        #         self.connectedClients[peerAddr].add_subscription(request.uuid)
        #         return _createResponse("success", "Subscription Stream added")
        #     return _createResponse("error", "UUID must be provided")
                
        # elif request.method == 'add-to-available-publication-stream' and request.uuid is not None:
        #     ''' local client tells the server to add a stream to its publication list since the local client is subscribed to that stream '''
        #     if request.uuid is not None:
        #         self.connectedClients[peerAddr].add_publication(request.uuid)
        #         print(self.availableStreams())
        #         return _createResponse("success", "Publication Stream added")
        #     return _createResponse("error", "UUID must be provided")
        
        # if request.method == 'stream-data':
        #     ''' sends the whole requested dataframe '''
        #     df = self._getStreamData(request.uuid)
        #     if df is None:
        #         return _createResponse(
        #             "error", f"No data found for stream {request.uuid}"
        #         )
        #     return _createResponse(
        #         "success",
        #         f" data found for stream {request.uuid}",
        #         df.to_json(orient='split'))
        
        # if request.uuid is None:
        #     return _createResponse("error", "Missing uuid parameter")
        
        # elif request.method == 'data-in-range':
        #     ''' sends requested dataframe of a particulare date range '''
        #     if not request.fromDate or not request.toDate:
        #         return _createResponse(
        #             "error", "Missing from_date or to_date parameter"
        #         )

        #     df = self._getStreamDataByDateRange(
        #         request.uuid, request.fromDate, request.toDate
        #     )
        #     if df is None:
        #         return _createResponse(
        #             "error",
        #             f"No data found for stream {request.uuid} in specified timestamp range",
        #         )

        #     if 'ts' in df.columns:
        #         df['ts'] = df['ts'].astype(str)
        #     return _createResponse(
        #         "success",
        #         f" data found for stream {request.uuid} in specified date range",
        #         df.to_json(orient='split'),
        #     )

        
        # elif request.method == 'record-at-or-before':
        #     ''' sends a sinlge row as dataframe of the record before or equal to specified timestamp '''
        #     try:
        #         if request.data is None:
        #             return _createResponse("error", "No timestamp data provided")
        #         timestamp_df = pd.read_json(StringIO(request.data), orient='split')
        #         timestamp = timestamp_df['ts'].iloc[0]
        #         df = self._getLastRecordBeforeTimestamp(
        #             request.uuid, timestamp
        #         )
        #         if df is None:
        #             return _createResponse(
        #                 "error",
        #                 f"No records found before timestamp for stream {request.uuid}",
        #             )

        #         if 'ts' in df.columns:
        #             df['ts'] = df['ts'].astype(str)
        #         return _createResponse(
        #             "success",
        #             f" records found before timestamp for stream {request.uuid}",
        #             df.to_json(orient='split'),
        #         )
        #     except Exception as e:
        #         return _createResponse(
        #             "error", f"Error processing timestamp request: {str(e)}"
        #         )
        
        # elif request.method == 'insert':
        #     ''' inserts the dataframe send in request into the database '''
        #     try:
        #         if request.data is None:
        #             return _createResponse(
        #                 "error", "No data provided"
        #             )
        #         data = pd.read_json(StringIO(request.data), orient='split')
        #         if request.replace:
        #             self.db.deleteTable(request.uuid)
        #             self.db.createTable(request.uuid)
        #         print(request.uuid in self.availableStreams())
        #         if request.isSubscription:
        #             if request.uuid in self.availableStreams():
        #                 try:
        #                     self.db._addSubDataToDatabase(request.uuid, data)
        #                     await self.updateSubscribers(request)
        #                     return _createResponse("success", "Data added to server database")
        #                 except Exception as e:
        #                     error("Error adding to database: ", e)
        #                     return _createResponse("error", "Failed to add data to server database")
        #             else:
        #                 print("Here")
        #                 return _createResponse("error", "Subcsription not in server list")
        #         else:
        #             success = self.db._addDataframeToDatabase(request.uuid, data)
        #             return _createResponse(
        #                 "success" if success else "error",
        #                 (
        #                     f"Data {'replaced' if request.replace else 'merged'} successfully"
        #                     if success
        #                     else "Failed to insert data"
        #                 ),
        #             )
        #     except Exception as e:
                # return _createResponse("error", f"Error inserting data: {str(e)}")

        # elif request.method == 'delete':
        #     ''' request to remove data from the database '''
        #     try:
        #         if request.data is not None:
        #             data = pd.read_json(StringIO(request.data), orient='split')
        #             timestamps = data['ts'].tolist()
        #             for ts in timestamps:
        #                 self.db.editTable('delete', request.uuid, timestamp=ts)
        #             return _createResponse("success", "Delete operation completed")
        #         else:
        #             self.db.deleteTable(request.uuid)
        #             return _createResponse(
        #                 "success", f"Table {request.uuid} deleted"
        #             )
        #     except Exception as e:
        #         return _createResponse("error", f"Error deleting data: {str(e)}")
            






