from satorilib.datamanager.client import DataClient
from satorilib.datamanager import Message
import asyncio
import pandas as pd
from satorilib.wallet.evrmore.identity import EvrmoreIdentity 
from satorineuron import config

async def main():
    walletPath = config.walletPath('wallet.yaml')
    client = DataClient("0.0.0.0", identity=EvrmoreIdentity(walletPath))
    df = pd.DataFrame({
        'value': [969.717144],
        'provider': 'krishna'
        }, index=['2025-11-06 04:30:06.341021'])
    
    await client.authenticate(islocal='engine')
    await client.insertStreamData('009bb819-b737-55f5-b4d7-d851316eceae', 
                                                          df, 
                                                          isSub=True)
    # await asyncio.sleep(10)
    # df = pd.DataFrame({
    #     'value': [42069.717144]
    #     }, index=['2026-11-06 04:30:06.341021'])
    # await client.insertStreamData('009bb819-b737-55f5-b4d7-d851316eceae', 
    #                                                       df, 
    #                                                       isSub=True)
    
asyncio.run(main())