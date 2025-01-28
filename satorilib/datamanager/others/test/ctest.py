# client_test.py
from satorilib.datamanager.client import DataClient
from satorilib.datamanager import Message
import asyncio

# TODO :
# Test for endpoints

# print and check the server state
# if client state needs change
# correct response is returned  

async def main():
    client = DataClient("localhost")
    
    # request = Message({
    #     'method': 'initiate-server-connection',
    #     'id': client._generateCallId(),
    #     'params': {'uuid': None}
    # })

    await client.sendRequest('0.0.0.1')
    await asyncio.sleep(5)
    
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