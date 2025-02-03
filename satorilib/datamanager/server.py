import websockets
import json
import pandas as pd
from typing import Any, Union
from io import StringIO
from satorilib.logging import INFO, setup, debug, info, warning, error
from satorilib.datamanager.helper import Message, Peer, ConnectedPeer
from satorilib.datamanager.manager import DataManager  
from satorilib.datamanager.api import DataServerApi 



class DataServer:
    def __init__(
        self,
        host: str,
        port: int = 24602,
    ):
        self.host = host
        self.port = port
        self.server = None 
        self.connectedClients: dict[Peer, ConnectedPeer] = {}
        self.dataManager: DataManager = DataManager() 

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
        peerAddr: Peer = Peer(*websocket.remote_address)
        self.connectedClients[peerAddr] = self.connectedClients.get(
            peerAddr, ConnectedPeer(peerAddr, websocket)
        )
        debug("Connected peer:", peerAddr, print=True)
        try:
            async for message in websocket:
                debug(f"Received request: {message}", print=True)
                response = await self.handleRequest(peerAddr, message)
                await self.connectedClients[peerAddr].websocket.send(
                    json.dumps(response)
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

        def _convertPeerInfoDict(data: dict) -> dict:
            convertedData = {}
            for subUuid, data in data.items():
                convertedData[subUuid] = data
            return convertedData

        request: Message = Message(json.loads(message))
        
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
                self.dataManager.pubSubMapping[sub_uuid] = data
            return DataServerApi.statusSuccess.createResponse('Pub-Sub map set in Server', request.id)

        elif request.method == DataServerApi.getPubsubMap.value:
            ''' this request fetches related pub-sub streams '''
            streamDict = _convertPeerInfoDict(self.dataManager.pubSubMapping)
            return DataServerApi.statusSuccess.createResponse('Pub-Sub map fetched from server', request.id, streamInfo=streamDict)

        elif request.method == DataServerApi.isStreamActive.value:
            ''' client asks the server whether it has the stream its trying to subscribe to in its publication list  '''
            if request.uuid in self.availableStreams():
                return DataServerApi.statusSuccess.createResponse('Subscription stream available to subscribe to', request.id)
            else:
                return DataServerApi.statusFail.createResponse('Subscription not available', request.id)
        
        elif request.method == DataServerApi.streamInactive.value:
            ''' local client tells the server is not active anymore '''
            publication_uuid = self.dataManager.pubSubMapping.get(request.uuid, {}).get('publicationUuid')
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
                df = self.dataManager.getStreamData(request.uuid)
                if not df.empty():
                    return DataServerApi.statusFail.createResponse('No data found for stream', request.id)
                return DataServerApi.statusSuccess.createResponse('data fetched for the stream', request.id, df.to_json(orient='split') )
            except Exception as e:
                return DataServerApi.statusFail.createResponse('Failed to fetch data', request.id)

        elif request.method == DataServerApi.getStreamDataByRange.value:
            ''' fetches dataframe of a particulare date range '''
            try:
                if not request.fromDate or not request.toDate:
                    return DataServerApi.statusFail.createResponse('Missing from_date or to_date parameter', request.id)
                df = self.dataManager.getStreamDataByDateRange(
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
                df = self.dataManager.getLastRecordBeforeTimestamp(
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
                    self.dataManager.db.deleteTable(request.uuid)
                    self.dataManager.db.createTable(request.uuid)
                if request.isSubscription:
                    if request.uuid in self.availableStreams():
                        self.dataManager.db._addSubDataToDatabase(request.uuid, data)
                        await self.updateSubscribers(request)
                        return DataServerApi.statusSuccess.createResponse('Data added to server database', request.id)
                    else:
                        return DataServerApi.statusFail.createResponse('Subcsription not in server list', request.id)
                else:
                    if self.dataManager.db._addDataframeToDatabase(request.uuid, data):
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
                        self.dataManager.db.editTable('delete', request.uuid, timestamp=ts)
                    return DataServerApi.statusSuccess.createResponse('Delete operation completed', request.id)
                # else: # TODO : should we delete the whole table?
                #     self.db.deleteTable(request.uuid)
                #     return DataServerApi.statusSuccess.createResponse('Table {request.uuid} deleted', request.id)
            except Exception as e:
                return DataServerApi.statusFail.createResponse(f'Error deleting data: {str(e)}', request.id)

        return DataServerApi.unknown.createResponse("Unknown request", request.id)





