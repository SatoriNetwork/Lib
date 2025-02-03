# client_test.py
from satorilib.datamanager.client import DataClient
from satorilib.datamanager import Message
import asyncio
import pandas as pd
from io import StringIO
import time

# TODO :
# Test for endpoints

# print and check the server state
# if client state needs change
# correct response is returned  

# async def main():
# client = DataClient("0.0.0.0")
# df = pd.DataFrame({
#     'date_time': ['2024-10-02 04:30:06.341020'],
#     'value': [969.717144]
#     })

# await client.isLocalEngineClient()
# time.sleep(10)
# await asyncio.sleep(10)

# async def diff():
#     print('diff')

async def main():
    client = DataClient("0.0.0.0")
    df = pd.DataFrame({
        'date_time': ['2024-10-02 04:30:06.341020'],
        'value': [969.717144]
        })


    response = await client.isLocalEngineClient()
    print(response.to_dict(True))
    # print('waiting for 6 seconds')
    # time.sleep(6)
    # print('waiting for 6 seconds')
    # await diff()
    # time.sleep(10)
    # print('done')
    # await diff()
    
    #print('waited for 10 seconds')
    #await asyncio.Event().wait()
    #await asyncio.Future()
    #await asyncio.sleep(10)
    # asyncio.create_task(client._keepAlive())
    #await client.isLocalEngineClient()

    # try:
    #     # Keep running until interrupted
    #     while True:
    #         await asyncio.sleep(5)
    # except KeyboardInterrupt:
    #     # Clean shutdown
    #     await client.disconnectAll()
    # print(response.to_dict(True))
    # response = await client.insertStreamData('04145e3c-ce99-5ef0-879f-9730e012aa26', df)
    
    # finalForm = pd.read_json(StringIO(response.data), orient='split')
    # print(finalForm)
    
    # response = await client.sendRequest(
    #     '0.0.0.0', 
    #     method='stream-data',
    #     uuid='04145e3c-ce99-5ef0-879f-9730e012aa26')

    # request = Message({
    #     'method': 'initiate-server-connection',
    #     'id': client._generateCallId(),
    #     'params': {'uuid': None}
    # })

    # request = Message({
    #     'method': 'initiate-server-connection',
    #     'id': client._generateCallId(),
    #     'params': {'uuid': None}
    # })

    # df = pd.DataFrame({
    #     'date_time': ['2024-10-02 04:30:05.341020'],
    #     'value': [969.717144],
    #     'id': ['lololol']
    #     })
    

    # response = await client.sendRequest(
    #     '0.0.0.0', 
    #     method='send-available-subscription')
    
    # print(response.streamInfo)

    # response = await client.sendRequest(
    #     '0.0.0.0', 
    #     method='add-available-subscription-streams',
    #     uuid='009bb819-b737-55f5-b4d7-d851316eceae')
    
    # print(response.status)
    # print(response.message)
    
    # await asyncio.sleep(10)
    
    # response = await client.sendRequest(
    #     '0.0.0.0', 
    #     method='send-available-subscription')
        # uuid='009bb819-b737-55f5-b4d7-d851316eceae',
        # data=df)
    # response = await client.passDataToServer(
    #     '0.0.0.0', 
    #     uuid='009bb819-b737-55f5-b4d7-d851316eceae',
    #     data=df)
    # print(response.status)
    # print(response.streamInfo)
    # await asyncio.sleep(5)
    
asyncio.run(main())


# endpoints to test in order

# 'initiate-server-connection'

# 'add-available-subscription-streams'

# 'add-available-publication-streams'

# 'confirm-subscription'

# 'send-available-subscription' : response.streamInfo

# 'stream-inactive' : check if the 

# 'stream-data'

# to send subscription message and check if its saved in the server's database
# await start.dataClient.passDataToServer(
            #     start.dataServerIp, 
            #     uuid=stream.streamId.uuid,
            #     data=dataForServer
            # )

    # dataForServer = pd.Dataframe({
    #         'date_time': [timestamp],
    #         'value': [69]
    #     })

# check if the response is recieved