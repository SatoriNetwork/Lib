import asyncio
from satorilib.datamanager import DataServer, DataClient, Message, DataServerApi
from satorilib.wallet.evrmore.identity import EvrmoreIdentity 
from satoriengine.veda.engine import Engine
from satorineuron import config
import pandas as pd

walletPath = config.walletPath('wallet.yaml')
uuid = "23dc3133-5b3a-5b27-803e-70a07cf3c4f7"

async def serverStartUp():
    dataServer = DataServer(host='0.0.0.0', identity=EvrmoreIdentity(walletPath))
    await dataServer.startServer()
    await asyncio.sleep(1)

async def authenticate():
    await serverStartUp()
    dataClient = DataClient('0.0.0.0', EvrmoreIdentity(walletPath))
    response: Message = await dataClient.authenticate()
    print(response.to_dict())
    # if response.status == DataServerApi.statusSuccess.value:
    #       print(response.auth)

async def checkIfLocalNeuronAuthenticated():
    await serverStartUp()
    
    dataClient = DataClient('0.0.0.0')
    response: Message = await dataClient.isLocalNeuronClient()
    if response.status == DataServerApi.statusSuccess.value:
          print(response.senderMsg)

async def checkIfLocalEngineAuthenticated():
    await serverStartUp()
    
    # await asyncio.sleep(5)
    
    dataClient = DataClient('0.0.0.0')
    pubSubInfo = {"23dc3133-5b3a-5b27-803e-70a07cf3c4f7":{"publicationUuid":"23dc3133-5b3a-5b27-803e-70a07cf3c4f7"}}
    await dataClient.setPubsubMap(pubSubInfo)
    response: Message = await dataClient.isLocalEngineClient()
    if response.status == DataServerApi.statusSuccess.value:
          print(response.senderMsg)
    
async def ifClientsetsPubSubInfoInDataServerCorrectly():
        await serverStartUp()

        dataClient = DataClient('0.0.0.0')
        pubSubInfo = {"23dc3133-5b3a-5b27-803e-70a07cf3c4f7":{"publicationUuid":"23dc3133-5b3a-5b27-803e-70a07cf3c4f7"}}
        response = await dataClient.setPubsubMap(pubSubInfo)
        if response.status == DataServerApi.statusSuccess.value:
            print(response.senderMsg)

async def ifClientgetPubSubInfoInDataServerCorrectly():
        await serverStartUp()

        dataClient = DataClient('0.0.0.0')
        pubSubInfo = {"23dc3133-5b3a-5b27-803e-70a07cf3c4f7":{"publicationUuid":"23dc3133-5b3a-5b27-803e-70a07cf3c4f7"}}
        await dataClient.setPubsubMap(pubSubInfo)
        response = await dataClient.getPubsubMap()
        if response.status == DataServerApi.statusSuccess.value:
            print(response.senderMsg)
            print(response.streamInfo)

async def checkIfStreamActive():
        await serverStartUp()

        dataClient = DataClient('0.0.0.0')
        response = await dataClient.isStreamActive('0.0.0.0',uuid)
        if response.status == DataServerApi.statusSuccess.value:
            print(response.senderMsg)

async def checkIfStreamInActive():
        await serverStartUp()

        dataClient = DataClient('0.0.0.0')
        await dataClient.isLocalNeuronClient()
        pubSubInfo = {"23dc3133-5b3a-5b27-803e-70a07cf3c4f7":{"publicationUuid":"23dc3133-5b3a-5b27-803e-70a07cf3c4f7"}}
        await dataClient.setPubsubMap(pubSubInfo)
        response = await dataClient.streamInactive(uuid)
        if response.status == DataServerApi.statusSuccess.value:
            print(response.senderMsg)

async def toCheckIfDataIsInsertedIntoClient():
    await serverStartUp()
    
    df = pd.DataFrame({
        'value': [969.717144],
        'hash':['bsjnlcs']
    }, index=['2024-10-02 04:30:06.341021'])


    dataClient = DataClient('0.0.0.0')
    response: Message = await dataClient.insertStreamData(uuid,df)
    if response.status == DataServerApi.statusSuccess.value:
          print(response.senderMsg)

async def checkToDeleteStreamData():
        await serverStartUp()

        df = pd.DataFrame({
        'value': [969.717144],
        'hash':['bsjnlcs']
    }, index=['2024-10-02 04:30:06.341021'])
        
        dataClient = DataClient('0.0.0.0')
        response = await dataClient.deleteStreamData(uuid,df)
        if response.status == DataServerApi.statusSuccess.value:
            print(response.senderMsg)

async def checkToGetRemoteStreamdata():
        await serverStartUp()

        dataClient = DataClient('0.0.0.0')
        response = await dataClient.getRemoteStreamData('0.0.0.0',uuid)
        if response.status == DataServerApi.statusSuccess.value:
            print(response.senderMsg)
            print(response.data)

async def checkToGetLocalStreamdata():
        await serverStartUp()

        dataClient = DataClient('0.0.0.0')
        response = await dataClient.getLocalStreamData(uuid)
        if response.status == DataServerApi.statusSuccess.value:
            print(response.senderMsg)
            print(response.data)

async def checkToGetAvailableSubscriptions():
        await serverStartUp()

        dataClient = DataClient('0.0.0.0')
        response = await dataClient.getAvailableSubscriptions('0.0.0.0')
        if response.status == DataServerApi.statusSuccess.value:
            print(response.senderMsg)
            print(response.streamInfo)

async def checkToGetStreamDataByRange():
        await serverStartUp()

        dataClient = DataClient('0.0.0.0')
        fromDate='2024-12-01 07:50:00.434717'
        toDate='2024-12-06 16:00:00.902535'
        response = await dataClient.getStreamDataByRange('0.0.0.0',uuid,fromDate,toDate)
        if response.status == DataServerApi.statusSuccess.value:
            print(response.senderMsg)
            print(response.data)

async def checkToGetStreamObservationByTime():
        await serverStartUp()

        dataClient = DataClient('0.0.0.0')
        toDate='2024-12-01 07:50:00.434717'
        response = await dataClient.getStreamObservationByTime('0.0.0.0',uuid,toDate)
        if response.status == DataServerApi.statusSuccess.value:
            print(response.senderMsg)
            print(response.data)

async def checkToAddActiveStream():
        await serverStartUp()

        dataClient = DataClient('0.0.0.0')
        response = await dataClient.addActiveStream(uuid)
        if response.status == DataServerApi.statusSuccess.value:
            print(response.senderMsg)

async def checkTo_addStreamToServer():
        await serverStartUp()

        dataClient = DataClient('0.0.0.0')
        response = await dataClient._addStreamToServer(subUuid=uuid,pubUuid=uuid)

async def checkToSubscribe():
        await serverStartUp()

        dataClient = DataClient('0.0.0.0')
        response = await dataClient.subscribe('0.0.0.0',uuid,uuid)
        if response.status == DataServerApi.statusSuccess.value:
            print(response.senderMsg)

asyncio.run(authenticate())

