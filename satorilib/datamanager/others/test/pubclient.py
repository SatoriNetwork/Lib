# client_test.py
import asyncio
import pandas as pd
from satorilib.datamanager import DataClient, Message, DataServerApi
from satorilib.wallet.evrmore.identity import EvrmoreIdentity 
from satorineuron import config


async def main():
    # df = pd.DataFrame({
    #     'value': [424.717144],
    #     # 'hash':['bsjnlct'],
    #     'provider': 'krishna'
    # }, index=['2025-02-19 05:30:06.341021'])

    walletPath = config.walletPath('wallet.yaml')
    # dataClient = DataClient('188.166.4.120', identity=EvrmoreIdentity(walletPath))
    dataClient = DataClient('::', identity=EvrmoreIdentity(walletPath))
    # response: Message = await dataClient.authenticate(islocal='engine')
    # response: Message = await dataClient.insertStreamData('009bb819-b737-55f5-b4d7-d851316eceae', 
    #                                                       df, 
    #                                                       isSub=True)
    # response: Message = await dataClient.addActiveStream('009bb819-b737-55f5-b4d7-d851316eceae')
    # response: Message = await dataClient.isStreamActive('159.65.144.150', '009bb819-b737-55f5-b4d7-d851316eceae')
    # await asyncio.sleep(20)
    # df = pd.DataFrame({
    #     'value': [424.717144],
    #     # 'hash':['bsjnlct'],
    #     'provider': 'krishna'
    # }, index=['2025-02-20 09:30:06.341021'])
    # response: Message = await dataClient.insertStreamData('009bb819-b737-55f5-b4d7-d851316eceae', 
    #                                                       df, 
    #                                                       isSub=True)
    # response: Message = await dataClient.isStreamActive('159.65.144.150', '009bb819-b737-55f5-b4d7-d851316eceae')
    # print(response.to_dict(True))
    # if response.status == DataServerApi.statusSuccess.value:
    print(response.senderMsg)
    await asyncio.Event().wait()

asyncio.run(main())