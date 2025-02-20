# client_test.py
import asyncio
import pandas as pd
from satorilib.datamanager import DataClient, Message, DataServerApi
from satorilib.wallet.evrmore.identity import EvrmoreIdentity 
from satorineuron import config


async def main():
    df = pd.DataFrame({
        'value': [968.717144],
        'hash':['bsjnlct']
    }, index=['2024-10-03 04:30:06.341021'])

    walletPath = config.walletPath('wallet.yaml')
    dataClient = DataClient('0.0.0.0', identity=EvrmoreIdentity(walletPath))
    response: Message = await dataClient.insertStreamData('009bb819-b737-55f5-b4d7-d851316eceae', 
                                                          df, 
                                                          isSub=True)
    if response.status == DataServerApi.statusSuccess.value:
          print(response.senderMsg)

asyncio.run(main())