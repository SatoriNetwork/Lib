# client_test.py
from satorilib.datamanager.client import DataClient
from satorilib.datamanager import Message
import asyncio

async def main():
    client = DataClient("localhost")
    await client.connectToServer()
    
    # Test the connection
    request = Message({
        'method': 'initiate-server-connection',
        'id': client._generateCallId(),
        'params': {'uuid': None}
    })
    await client.sendRequest('0.0.0.1')
    await asyncio.sleep(5)
    await client.serverWs.send(request.to_json())
    
    await asyncio.sleep(30)  # Keep running for 30s

asyncio.run(main())