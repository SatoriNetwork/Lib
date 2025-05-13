# client_test.py
import asyncio
import pandas as pd
from satorilib.datamanager import DataClient, Message, DataServerApi
from satorilib.wallet.evrmore.identity import EvrmoreIdentity 
from satorineuron import config


async def main():
    df = pd.DataFrame({
        'value': [43.717144],
        # 'hash':['bsjnlct'],
        'provider': 'krishna'
    }, index=['2025-05-13 06:57:01.115730'])

    walletPath = config.walletPath('wallet.yaml')
    # dataClient = DataClient('188.166.4.120', identity=EvrmoreIdentity(walletPath))
    dataClient = DataClient('0.0.0.0', identity=EvrmoreIdentity(walletPath))
    # await dataClient.addActiveStream('009bb819-b737-55f5-b4d7-d851316eceae')
    response = await dataClient.send(
                    peerAddr=('0.0.0.0', 24604), 
                    request=Message(DataServerApi.addActiveStream.createRequest('168467c1-99a1-5868-83f8-64e817758030'))
                )
    # response = await dataClient.send(
    #                 peerAddr=('0.0.0.0', 24604), 
    #                 request=Message(DataServerApi.addActiveStream.createRequest('f85266a9-1b16-5802-84fe-862611744739'))
    #             )
    # print(response.to_dict())

    response = await dataClient.getAvailableSubscriptions(
                            peerHost='0.0.0.0',
                            peerPort=24604)
    
    print(response.to_dict())
    # response = await dataClient.getAvailableSubscriptions(
    #                         peerHost='45.113.226.219',
    #                         peerPort=24603)
    # response = await dataClient.getAvailableSubscriptions(
    #                         peerHost='193.108.116.96',
    #                         peerPort=24611)
                            # uuid='f85266a9-1b16-5802-84fe-862611744739')
    msg = Message({
                    'method': DataServerApi.insertStreamData.value,
                    'status': 'success',
                    'sub': True,
                    'params': {'uuid': '168467c1-99a1-5868-83f8-64e817758030'},
                    'data': df,
                    # **({'stream_info': self.dataManager.transferProtocolPayload[request.uuid] if request.uuid in self.dataManager.transferProtocolPayload else []} 
                    #     if self.dataManager.transferProtocol == 'p2p-proactive' and self.connectedClients[peerAddr].isLocal else {})
                })
    # try:
    
    # await asyncio.sleep(50)
    response = await dataClient.send(
        peerAddr=('0.0.0.0', 24604),
        request=msg,
        sendOnly=True
        )
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