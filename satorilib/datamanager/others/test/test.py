import asyncio
from satorilib.datamanager import DataServer, DataClient, Message, DataServerApi

async def checkIfLocalNeuronAuthenticated():
    dataServer = DataServer('0.0.0.0')
    await dataServer.startServer()
    await asyncio.sleep(5)
    
    dataClient = DataClient('0.0.0.0')
    response: Message = await dataClient.isLocalNeuronClient()
    if response.status == DataServerApi.statusSuccess.value:
          print(response.senderMsg)
    
def ifClientsetsPubSubInfoInDataServerCorrectly():
        # dataserver - initialize and start listening
        # await asyncio.sleep(10)

        # initialize client
        # response = await dataClient.setPubSub(pubSubInfo)
        # response.status == DataServerApi.statusSuccess.value:
        #     print(response.senderMsg)
        pass

async def toCheckIfDataIsInsertedIntoClient():
    dataServer = DataServer('0.0.0.0')
    await dataServer.startServer()
    await asyncio.sleep(5)
    
    # uuid = some uuid in your database

    # df = pd.DataFrame({
    #     'date_time': ['2024-10-02 04:30:06.341020'],
    #     'value': [969.717144]
    #     })
    # df['date_time'] = pd.to_datetime(df['date_time'])
    # df.set_index('date_time', inplace=True)


    dataClient = DataClient('0.0.0.0')
    # response: Message = await dataClient.insertStreamData()
    response: Message = await dataClient.isLocalNeuronClient()
    if response.status == DataServerApi.statusSuccess.value:
          print(response.senderMsg)

asyncio.run(toCheckIfDataIsInsertedIntoClient())