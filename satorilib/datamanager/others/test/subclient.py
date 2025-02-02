from satorilib.datamanager.client import DataClient
from satorilib.datamanager import Message
import asyncio
import pandas as pd
from io import StringIO

async def main():
    client = DataClient("0.0.0.0")
    df = pd.DataFrame({
        'date_time': ['2024-10-02 04:30:06.341020'],
        'value': [969.717144]
        })
    
    await client.isLocalNeuronClient()
    await asyncio.sleep(5)
    
asyncio.run(main())