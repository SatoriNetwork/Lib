# client_test.py
import asyncio
import pandas as pd
from satorilib.datamanager import DataClient, Message, DataServerApi
from satorilib.wallet.evrmore.identity import EvrmoreIdentity 
from satorineuron import config


async def main():
    df = pd.DataFrame({
        'value': [424.717144],
        # 'hash':['bsjnlct'],
        'provider': 'krishna'
    }, index=['2025-02-05 03:40:01.115730'])

    walletPath = config.walletPath('wallet.yaml')
    # dataClient = DataClient('188.166.4.120', identity=EvrmoreIdentity(walletPath))
    dataClient = DataClient('0.0.0.0', identity=EvrmoreIdentity(walletPath))
    response = await dataClient.isStreamActive(
                            peerHost='0.0.0.0',
                            peerPort=24604,
                            uuid='883f30d2-854c-5dcf-aa0f-1a0e9ad21df7')
    # msg = Message({
    #                 'method': DataServerApi.insertStreamData.value,
    #                 'status': 'success',
    #                 'sub': True,
    #                 'params': {'uuid': '9b672d88-f38f-5522-8fe5-4d16d9fe1fe3'},
    #                 'data': df,
    #                 # **({'stream_info': self.dataManager.transferProtocolPayload[request.uuid] if request.uuid in self.dataManager.transferProtocolPayload else []} 
    #                 #     if self.dataManager.transferProtocol == 'p2p-proactive' and self.connectedClients[peerAddr].isLocal else {})
    #             })
    # try:
    # response = await dataClient.send(
    #     peerAddr=('::', 24600),
    #     request=msg
    #     )
    # await dataClient.insertStreamDataForRemote(
    #     '::',
    #     24600,
    #     '9b672d88-f38f-5522-8fe5-4d16d9fe1fe3',
    #     df,
    #     isSub=True
    # )
    # except:
    #     print("error sending": )
    
    # response: Message = await dataClient.authenticate()
    # response: Message = await dataClient.insertStreamData('9b672d88-f38f-5522-8fe5-4d16d9fe1fe3', 
    #                                                       df, 
    #                                                       isSub=True)
    # response: Message = await dataClient.addActiveStream('009bb819-b737-55f5-b4d7-d851316eceae')
    print(response.to_dict())
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
    # print(response.senderMsg)
    await asyncio.Event().wait()

asyncio.run(main())