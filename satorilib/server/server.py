'''
Here's plan for the server - python server, you checkin with it,
it returns a key you use to make a websocket connection with the pubsub server.

# TODO:
- [ ] implement DTOs for all the server calls
- [ ] implement Swagger on the server / python packages...
{
    "DTO": "Proposal",
    "error": null,
    "data": {
        "id": 1,
        "author": "22a85fb71485c6d7c62a3784c5549bd3849d0afa3ee44ce3f9ea5541e4c56402d8",
        "title": "Proposal Title",
        "description": "Proposal Description",
        ...
    }
}
JSON -> EXTRACT DATA -> Python Object -> DTO -> JSON
{{ proposal.author }}
'''
from typing import Union
from functools import partial
import base64
import time
import json
import requests
from satorilib import logging
from satorilib.utils.time import timeToTimestamp
from satorilib.wallet import Wallet
from satorilib.concepts.structs import Stream
from satorilib.server.api import ProposalSchema, VoteSchema
from satorilib.utils.json import sanitizeJson
from requests.exceptions import RequestException
import json
import traceback
import datetime as dt


class SatoriServerClient(object):
    def __init__(
        self,
        wallet: Wallet,
        url: str = None,
        sendingUrl: str = None,
        *args, **kwargs
    ):
        self.wallet = wallet
        self.url = url or 'https://central.satorinet.io'
        self.sendingUrl = sendingUrl or 'https://mundo.satorinet.io'
        self.topicTime: dict[str, float] = {}
        self.lastCheckin: int = 0

    def setTopicTime(self, topic: str):
        self.topicTime[topic] = time.time()

    def _getChallenge(self):
        # return requests.get(self.url + '/time').text
        return str(time.time())

    def _makeAuthenticatedCall(
        self,
        function: callable,
        endpoint: str,
        url: str = None,
        payload: Union[str, dict, None] = None,
        challenge: str = None,
        useWallet: Wallet = None,
        extraHeaders: Union[dict, None] = None,
        raiseForStatus: bool = True,
    ) -> requests.Response:
        if isinstance(payload, dict):
            payload = json.dumps(payload)

        if payload is not None:
            logging.info(
                f'outgoing: {endpoint}',
                payload[0:40], f'{"..." if len(payload) > 40 else ""}',
                print=True)
        r = function(
            (url or self.url) + endpoint,
            headers={
                **(useWallet or self.wallet).authPayload(
                    asDict=True,
                    challenge=challenge or self._getChallenge()),
                **(extraHeaders or {}),
            },
            json=payload)
        if raiseForStatus:
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logging.error('authenticated server err:',
                              r.text, e, color='red')
                r.raise_for_status()
        logging.info(
            f'incoming: {endpoint}',
            r.text[0:40], f'{"..." if len(r.text) > 40 else ""}',
            print=True)
        return r

    def _makeUnauthenticatedCall(
        self,
        function: callable,
        endpoint: str,
        url: str = None,
        headers: Union[dict, None] = None,
        payload: Union[str, bytes, None] = None,
    ):
        logging.info(
            'outgoing Satori server message to ',
            endpoint,
            print=True)
        data = None
        json = None
        if isinstance(payload, bytes):
            headers = headers or {'Content-Type': 'application/octet-stream'}
            data = payload
        elif isinstance(payload, str):
            headers = headers or {'Content-Type': 'application/json'}
            json = payload
        else:
            headers = headers or {}
        r = function(
            (url or self.url) + endpoint,
            headers=headers,
            json=json,
            data=data)
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.error("unauth'ed server err:", r.text, e, color='red')
            r.raise_for_status()
        logging.info(
            'incoming Satori server message:',
            r.text[0:40], f'{"..." if len(r.text) > 40 else ""}',
            print=True)
        return r

    def registerWallet(self):
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/register/wallet',
            payload=self.wallet.registerPayload())

    def registerStream(self, stream: dict, payload: str = None):
        ''' publish stream {'source': 'test', 'name': 'stream1', 'target': 'target'}'''
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/register/stream',
            payload=payload or json.dumps(stream))

    def registerSubscription(self, subscription: dict, payload: str = None):
        ''' subscribe to stream '''
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/register/subscription',
            payload=payload or json.dumps(subscription))

    def registerPin(self, pin: dict, payload: str = None):
        '''
        report a pin to the server.
        example: {
            'author': {'pubkey': '22a85fb71485c6d7c62a3784c5549bd3849d0afa3ee44ce3f9ea5541e4c56402d8'},
            'stream': {'source': 'satori', 'pubkey': '22a85fb71485c6d7c62a3784c5549bd3849d0afa3ee44ce3f9ea5541e4c56402d8', 'stream': 'stream1', 'target': 'target', 'cadence': None, 'offset': None, 'datatype': None, 'url': None, 'description': 'raw data'},,
            'ipns': 'ipns',
            'ipfs': 'ipfs',
            'disk': 1,
            'count': 27},
        '''
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/register/pin',
            payload=payload or json.dumps(pin))

    def requestPrimary(self):
        ''' subscribe to primary data stream and and publish prediction '''
        return self._makeAuthenticatedCall(
            function=requests.get,
            endpoint='/request/primary')

    def getStreams(self, stream: dict, payload: str = None):
        ''' subscribe to primary data stream and and publish prediction '''
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/get/streams',
            payload=payload or json.dumps(stream))

    def myStreams(self):
        ''' subscribe to primary data stream and and publish prediction '''
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/my/streams',
            payload='{}')

    def removeStream(self, stream: dict = None, payload: str = None):
        ''' removes a stream from the server '''
        if payload is None and stream is None:
            raise ValueError('stream or payload must be provided')
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/remove/stream',
            payload=payload or json.dumps(stream or {}))

    def checkin(self, referrer: str = None) -> dict:
        challenge = self._getChallenge()
        response = self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/checkin',
            payload=self.wallet.registerPayload(challenge=challenge),
            challenge=challenge,
            extraHeaders={'referrer': referrer} if referrer else {},
            raiseForStatus=False)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.error('unable to checkin:', response.text, e, color='red')
            return {'ERROR': response.text}
        self.lastCheckin = time.time()
        return response.json()

    def checkinCheck(self) -> bool:
        challenge = self._getChallenge()
        response = self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/checkin/check',
            payload=self.wallet.registerPayload(challenge=challenge),
            challenge=challenge,
            extraHeaders={'changesSince': timeToTimestamp(self.lastCheckin)},
            raiseForStatus=False)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.error('unable to checkin:', response.text, e, color='red')
            return False
        return response.text.lower() == 'true'

    def requestSimplePartial(self, network: str):
        ''' sends a satori partial transaction to the server '''
        return self._makeUnauthenticatedCall(
            function=requests.get,
            url=self.sendingUrl,
            endpoint=f'/simple_partial/request/{network}').json()

    def broadcastSimplePartial(
        self,
        tx: bytes,
        feeSatsReserved: float,
        reportedFeeSats: float,
        walletId: float,
        network: str
    ):
        ''' sends a satori partial transaction to the server '''
        return self._makeUnauthenticatedCall(
            function=requests.post,
            url=self.sendingUrl,
            endpoint=f'/simple_partial/broadcast/{network}/{feeSatsReserved}/{reportedFeeSats}/{walletId}',
            payload=tx)

    def broadcastBridgeSimplePartial(
        self,
        tx: bytes,
        feeSatsReserved: float,
        reportedFeeSats: float,
        walletId: float,
        network: str
    ):
        ''' sends a satori partial transaction to the server '''
        return self._makeUnauthenticatedCall(
            function=requests.post,
            url=self.sendingUrl,
            endpoint=f'/simple/bridge/partial/broadcast/{network}/{feeSatsReserved}/{reportedFeeSats}/{walletId}',
            payload=tx)

    def removeWalletAlias(self):
        ''' removes the wallet alias from the server '''
        return self._makeAuthenticatedCall(
            function=requests.get,
            endpoint='/remove_wallet_alias')

    def updateWalletAlias(self, alias: str):
        ''' removes the wallet alias from the server '''
        return self._makeAuthenticatedCall(
            function=requests.get,
            endpoint='/update_wallet_alias/' + alias)

    def getWalletAlias(self):
        ''' removes the wallet alias from the server '''
        return self._makeAuthenticatedCall(
            function=requests.get,
            endpoint='/get_wallet_alias').text

    def getManifestVote(self, wallet: Wallet = None):
        return self._makeUnauthenticatedCall(
            function=requests.get,
            endpoint=(
                f'/votes_for/manifest/{wallet.publicKey}'
                if isinstance(wallet, Wallet) else '/votes_for/manifest')).json()

    def getSanctionVote(self, wallet: Wallet = None, vault: Wallet = None):
        # logging.debug('vault', vault, color='yellow')
        walletPubkey = wallet.publicKey if isinstance(
            wallet, Wallet) else 'None'
        vaultPubkey = vault.publicKey if isinstance(vault, Wallet) else 'None'
        # logging.debug(
        #    f'/votes_for/sanction/{walletPubkey}/{vaultPubkey}', color='yellow')
        return self._makeUnauthenticatedCall(
            function=requests.get,
            endpoint=f'/votes_for/sanction/{walletPubkey}/{vaultPubkey}').json()

    def getSearchStreams(self, searchText: str = None):
        '''
        returns [{
            'author': 27790,
            'cadence': 600.0,
            'datatype': 'float',
            'description': 'Price AED 10min interval coinbase',
            'oracle_address': 'EHJKq4EW2GfGBvhweasMXCZBVbAaTuDERS',
            'oracle_alias': 'WilQSL_x10',
            'oracle_pubkey': '03e3f3a15c2e174cac7ef8d1d9ff81e9d4ef7e33a59c20cc5cc142f9c69493f306',
            'predicting_id': 0,
            'sanctioned': 0,
            'source': 'satori',
            'stream': 'Coinbase.AED.USDT',
            'stream_created_ts': 'Tue, 09 Jul 2024 10:20:11 GMT',
            'stream_id': 326076,
            'tags': 'AED, coinbase',
            'target': 'data.rates.AED',
            'total_vote': 6537.669052915435,
            'url': 'https://api.coinbase.com/v2/exchange-rates',
            'utc_offset': 227.0,
            'vote': 33.333333333333336},...]
        '''

        def cleanAndSort(streams: str, searchText: str = None):
            # Commenting down as of now, will be used in future if we need to make the call to server for search streams
            # as of now we have limited streams so we can search in client side
            # if searchText:
            #     searchedStreams = [s for s in streams if searchText.lower() in s['stream'].lower()]
            #     return sanitizeJson(searchedStreams)
            sanitizedStreams = sanitizeJson(streams)
            # sorting streams based on vote and total_vote
            sortedStreams = sorted(
                sanitizedStreams,
                key=lambda x: (x.get('vote', 0) == 0, -
                               x.get('vote', 0), -x.get('total_vote', 0))
            )
            return sortedStreams

        return cleanAndSort(
            streams=self._makeUnauthenticatedCall(
                function=requests.post,
                endpoint='/streams/search',
                payload=json.dumps({'address': self.wallet.address})).json(),
            searchText=searchText)

    def incrementVote(self, streamId: str):
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/vote_on/sanction/incremental',
            payload=json.dumps({'streamId': streamId})).text

    def removeVote(self, streamId: str):
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/clear_vote_on/sanction/incremental',
            payload=json.dumps({'streamId': streamId})).text

    def getObservations(self, streamId: str):
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/observations/list',
            payload=json.dumps({'streamId': streamId})).text

    def submitMaifestVote(self, wallet: Wallet, votes: dict[str, int]):
        # todo authenticate the vault instead
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/vote_on/manifest',
            useWallet=wallet,
            payload=json.dumps(votes or {})).text

    def submitSanctionVote(self, wallet: Wallet, votes: dict[str, int]):
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/vote_on/sanction',
            useWallet=wallet,
            payload=json.dumps(votes or {})).text

    def removeSanctionVote(self, wallet: Wallet):
        return self._makeAuthenticatedCall(
            function=requests.Get,
            endpoint='/clear_votes_on/sanction',
            useWallet=wallet).text

    def poolParticipants(self, vaultAddress: str):
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/pool/participants',
            payload=json.dumps({'vaultAddress': vaultAddress})).text

    def pinDepinStream(self, stream: dict = None) -> tuple[bool, str]:
        ''' removes a stream from the server '''
        if stream is None:
            raise ValueError('stream must be provided')
        response = self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/register/subscription/pindepin',
            payload=json.dumps(stream))
        if response.status_code < 400:
            return response.json().get('success'), response.json().get('result')
        return False, ''

    def minedToVault(self) -> Union[bool, None]:
        '''  '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/mine_to_vault/status')
            if response.status_code > 399:
                return None
            if response.text in ['', 'null', 'None', 'NULL']:
                return False
        except Exception as e:
            logging.warning(
                'unable to determine status of Mine-To-Vault feature due to connection timeout; try again Later.', e, color='yellow')
            return None
        return True

    def mineToAddressStatus(self) -> Union[str, None]:
        ''' get reward address '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/mine/to/address')
            if response.status_code > 399:
                return 'Unknown'
            if response.text in ['null', 'None', 'NULL']:
                return ''
            return response.text
        except Exception as e:
            logging.warning(
                'unable to get reward address; try again Later.', e, color='yellow')
            return None
        return None

    def setRewardAddress(
        self,
        signature: Union[str, bytes],
        pubkey: str,
        address: str,
        usingVault: bool = False,
    ) -> tuple[bool, str]:
        ''' just like mine to address but using the wallet '''
        try:
            if isinstance(signature, bytes):
                signature = signature.decode()
            if usingVault:
                js = json.dumps({
                    'vaultSignature': signature,
                    'vaultPubkey': pubkey,
                    'address': address})
            else:
                js = json.dumps({
                    'signature': signature,
                    'pubkey': pubkey,
                    'address': address})
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/mine/to/address',
                payload=js)
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to set reward address; try again Later.', e, color='yellow')
            return False, ''

    def stakeForAddress(
        self,
        vaultSignature: Union[str, bytes],
        vaultPubkey: str,
        address: str
    ) -> tuple[bool, str]:
        ''' add stake address '''
        try:
            if isinstance(vaultSignature, bytes):
                vaultSignature = vaultSignature.decode()
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/stake/for/address',
                raiseForStatus=False,
                payload=json.dumps({
                    'vaultSignature': vaultSignature,
                    'vaultPubkey': vaultPubkey,
                    'address': address}))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to determine status of mine to address feature due to connection timeout; try again Later.', e, color='yellow')
            return False, ''

    def lendToAddress(
        self,
        vaultSignature: Union[str, bytes],
        vaultPubkey: str,
        address: str
    ) -> tuple[bool, str]:
        ''' add lend address '''
        try:
            if isinstance(vaultSignature, bytes):
                vaultSignature = vaultSignature.decode()
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/stake/lend/to/address',
                raiseForStatus=False,
                payload=json.dumps({
                    'vaultSignature': vaultSignature,
                    'vaultPubkey': vaultPubkey,
                    'address': address}))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to determine status of mine to address feature due to connection timeout; try again Later.', e, color='yellow')
            return False, ''

    def lendRemove(self) -> tuple[bool, dict]:
        ''' removes a stream from the server '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/stake/lend/remove')
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to stakeProxyRemove due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def lendAddress(self) -> Union[str, None]:
        ''' get lending address '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/stake/lend/address')
            if response.status_code > 399:
                return 'Unknown'
            if response.text in ['null', 'None', 'NULL']:
                return ''
            return response.text
        except Exception as e:
            logging.warning(
                'unable to get reward address; try again Later.', e, color='yellow')
            return ''

    def registerVault(
        self,
        walletSignature: Union[str, bytes],
        vaultSignature: Union[str, bytes],
        vaultPubkey: str,
        address: str,
    ) -> tuple[bool, str]:
        ''' removes a stream from the server '''
        if isinstance(walletSignature, bytes):
            walletSignature = walletSignature.decode()
        if isinstance(vaultSignature, bytes):
            vaultSignature = vaultSignature.decode()
        try:
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/register/vault',
                payload=json.dumps({
                    'walletSignature': walletSignature,
                    'vaultSignature': vaultSignature,
                    'vaultPubkey': vaultPubkey,
                    'address': address}))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to register vault address due to connection timeout; try again Later.', e, color='yellow')
            return False, ''

    def enableMineToVault(
        self,
        walletSignature: Union[str, bytes],
        vaultSignature: Union[str, bytes],
        vaultPubkey: str,
        address: str,
    ) -> tuple[bool, str]:
        ''' removes a stream from the server '''
        if isinstance(walletSignature, bytes):
            walletSignature = walletSignature.decode()
        if isinstance(vaultSignature, bytes):
            vaultSignature = vaultSignature.decode()
        try:
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/mine_to_vault/enable',
                payload=json.dumps({
                    'walletSignature': walletSignature,
                    'vaultSignature': vaultSignature,
                    'vaultPubkey': vaultPubkey,
                    'address': address}))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to enable status of Mine-To-Vault feature due to connection timeout; try again Later.', e, color='yellow')
            return False, ''

    def disableMineToVault(
        self,
        walletSignature: Union[str, bytes],
        vaultSignature: Union[str, bytes],
        vaultPubkey: str,
        address: str,
    ) -> tuple[bool, str]:
        ''' removes a stream from the server '''
        if isinstance(walletSignature, bytes):
            walletSignature = walletSignature.decode()
        if isinstance(vaultSignature, bytes):
            vaultSignature = vaultSignature.decode()
        try:
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/mine_to_vault/disable',
                payload=json.dumps({
                    'walletSignature': walletSignature,
                    'vaultSignature': vaultSignature,
                    'vaultPubkey': vaultPubkey,
                    'address': address}))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to disable status of Mine-To-Vault feature due to connection timeout; try again Later.', e, color='yellow')
            return False, ''

    def fetchWalletStatsDaily(self) -> str:
        ''' gets wallet stats '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/wallet/stats/daily')
            return response.json()
        except Exception as e:
            logging.warning(
                'unable to disable status of Mine-To-Vault feature due to connection timeout; try again Later.', e, color='yellow')
            return ''

    def stakeCheck(self) -> bool:
        ''' gets wallet stats '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/stake/check')
            if response.text == 'TRUE':
                return True
        except Exception as e:
            logging.warning(
                'unable to disable status of Mine-To-Vault feature due to connection timeout; try again Later.', e, color='yellow')
            return False
        return False

    def setEthAddress(self, ethAddress: str) -> tuple[bool, dict]:
        ''' removes a stream from the server '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/set/eth/address',
                payload=json.dumps({'ethAddress': ethAddress}))
            return response.status_code < 400, response.json()
        except Exception as e:
            logging.warning(
                'unable to claim beta due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def poolAddresses(self) -> tuple[bool, dict]:
        ''' removes a stream from the server '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/stake/lend/addresses')
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to stakeProxyRequest due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def poolAddressRemove(self, lend_id: str):
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/stake/lend/address/remove',
            payload=json.dumps({'lend_id': lend_id})).text

    def stakeProxyChildren(self) -> tuple[bool, dict]:
        ''' removes a stream from the server '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/stake/proxy/children')
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to stakeProxyRequest due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def stakeProxyCharity(self, address: str, childId: int) -> tuple[bool, dict]:
        ''' charity for stake '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/stake/proxy/charity',
                payload=json.dumps({
                    'child': address,
                    **({} if childId in [None, 0, '0'] else {'childId': childId})
                }))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to stakeProxyCharity due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def stakeProxyCharityNot(self, address: str, childId: int) -> tuple[bool, dict]:
        ''' no charity for stake '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/stake/proxy/charity/not',
                payload=json.dumps({
                    'child': address,
                    **({} if childId in [None, 0, '0'] else {'childId': childId})
                }))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to stakeProxyCharityNot due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def delegateGet(self) -> tuple[bool, str]:
        ''' my delegate '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/stake/proxy/delegate')
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to delegateGet due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def delegateRemove(self) -> tuple[bool, str]:
        ''' my delegate '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/stake/proxy/delegate/remove')
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to delegateRemove due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def stakeProxyRemove(self, address: str, childId: int) -> tuple[bool, dict]:
        ''' removes a stream from the server '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/stake/proxy/remove',
                payload=json.dumps({'child': address, 'childId': childId}))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to stakeProxyRemove due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def publish(
        self,
        topic: str,
        data: str,
        observationTime: str,
        observationHash: str,
        isPrediction: bool = True,
        useAuthorizedCall: bool = True,
    ) -> Union[bool, None]:
        ''' publish predictions '''
        #logging.info(f'publishing', color='blue')
        # if not isPrediction and self.topicTime.get(topic, 0) > time.time() - (Stream.minimumCadence*.95):
        #    return
        # if isPrediction and self.topicTime.get(topic, 0) > time.time() - 60*60:
        #    return
        if self.topicTime.get(topic, 0) > time.time() - (Stream.minimumCadence*.95):
            return
        self.setTopicTime(topic)
        try:
            if useAuthorizedCall:
                response = self._makeAuthenticatedCall(
                    function=requests.post,
                    endpoint='/record/prediction/authed' if isPrediction else '/record/observation/authed',
                    payload=json.dumps({
                        'topic': topic,
                        'data': str(data),
                        'time': str(observationTime),
                        'hash': str(observationHash),
                    }))
            else:
                response = self._makeUnauthenticatedCall(
                    function=requests.post,
                    endpoint='/record/prediction' if isPrediction else '/record/observation',
                    payload=json.dumps({
                        'topic': topic,
                        'data': str(data),
                        'time': str(observationTime),
                        'hash': str(observationHash),
                    }))
            # response = self._makeAuthenticatedCall(
            #    function=requests.get,
            #    endpoint='/record/prediction')
            if response.status_code == 200:
                return True
            if response.status_code > 399:
                return None
            if response.text.lower() in ['fail', 'null', 'none', 'error']:
                return False
        except Exception as _:
            # logging.warning(
            #    'unable to determine if prediction was accepted; try again Later.', e, color='yellow')
            return None
        return True

    # def getProposalById(self, proposal_id: str) -> dict:
    #    try:
    #        response = self._makeUnauthenticatedCall(
    #            function=requests.get,
    #            endpoint=f'/proposals/get/{proposal_id}'  # Update endpoint path
    #        )
    #        if response.status_code == 200:
    #            return response.json()
    #        else:
    #            logging.error(f"Failed to get proposal. Status code: {response.status_code}")
    #            return None
    #    except Exception as e:
    #        logging.error(f"Error occurred while fetching proposal: {str(e)}")
    #        return None

    def getProposals(self):
        """
        Function to get all proposals by calling the API endpoint.
        """
        try:
            response = self._makeUnauthenticatedCall(
                function=requests.get,
                endpoint='/proposals/get/all'
            )
            if response.status_code == 200:
                proposals = response.json()
                return proposals
            else:
                logging.error(
                    f"Failed to get proposals. Status code: {response.status_code}", color='red')
                return []
        except requests.RequestException as e:
            logging.error(
                f"Error occurred while fetching proposals: {str(e)}", color='red')
            return []

    def getApprovedProposals(self):
        """
        Function to get all approved proposals by calling the API endpoint.
        """
        try:
            response = self._makeUnauthenticatedCall(
                function=requests.get,
                endpoint='/proposals/get/approved'
            )
            if response.status_code == 200:
                proposals = response.json()
                return proposals
            else:
                logging.error(
                    f"Failed to get approved proposals. Status code: {response.status_code}", color='red')
                return []
        except requests.RequestException as e:
            logging.error(
                f"Error occurred while fetching approved proposals: {str(e)}", color='red')
            return []

    def submitProposal(self, proposal_data: dict) -> tuple[bool, dict]:
        '''submits proposal'''
        try:
            # Ensure options is a JSON string
            if 'options' in proposal_data and isinstance(proposal_data['options'], list):
                proposal_data['options'] = json.dumps(proposal_data['options'])

            # Convert the entire proposal_data to a JSON string
            proposal_json_string = json.dumps(proposal_data)

            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/proposal/submit',
                payload=proposal_json_string
            )
            if response.status_code < 400:
                return True, response.text
            else:
                error_message = f"Server returned status code {response.status_code}: {response.text}"
                logging.error(f"Error in submitProposal: {error_message}")
                return False, {"error": error_message}

        except RequestException as re:
            error_message = f"Request error in submitProposal: {str(re)}"
            logging.error(error_message)
            logging.error(traceback.format_exc())
            return False, {"error": error_message}
        except Exception as e:
            error_message = f"Unexpected error in submitProposal: {str(e)}"
            logging.error(error_message)
            logging.error(traceback.format_exc())
            return False, {"error": error_message}

    def getProposalById(self, proposal_id: str) -> dict:
        """
        Function to get a specific proposal by ID by calling the API endpoint.
        """
        try:
            response = self._makeUnauthenticatedCall(
                function=requests.get,
                endpoint=f'/proposal/{proposal_id}'
            )
            if response.status_code == 200:
                return response.json()['proposal']
            else:
                logging.error(
                    f"Failed to get proposal. Status code: {response.status_code}",
                    extra={'color': 'red'}
                )
                return None
        except requests.RequestException as e:
            logging.error(
                f"Error occurred while fetching proposal: {str(e)}",
                extra={'color': 'red'}
            )
            return None

    def getProposalVotes(self, proposal_id: str, format_type: str = None) -> dict:
        '''Gets proposal votes with option for raw or processed format'''
        try:
            endpoint = f'/proposal/votes/get/{proposal_id}'
            if format_type:
                endpoint += f'?format={format_type}'

            response = self._makeUnauthenticatedCall(
                function=requests.get,
                endpoint=endpoint
            )

            if response.status_code == 200:
                return response.json()
            else:
                error_message = f"Server returned status code {response.status_code}: {response.text}"
                return {'status': 'error', 'message': error_message}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def getExpiredProposals(self) -> dict:
        """
        Fetches expired proposals
        """
        try:
            response = self._makeUnauthenticatedCall(
                function=requests.get,
                endpoint='/proposals/expired'
            )
            if response.status_code == 200:
                return {'status': 'success', 'proposals': response.json()}
            else:
                error_message = f"Server returned status code {response.status_code}: {response.text}"
                return {'status': 'error', 'message': error_message}
        except Exception as e:
            error_message = f"Error in getExpiredProposals: {str(e)}"
            return {'status': 'error', 'message': error_message}

    def isApprovedAdmin(self, address: str) -> bool:
        """Check if a wallet address has admin rights"""
        if address not in {
            "ES48mkqM5wMjoaZZLyezfrMXowWuhZ8u66",
            "Efnsr27fc276Wp7hbAqZ5uo7Rn4ybrUqmi",
            "EQGB7cBW3HvafARDoYsgceJS2W7ZhKe3b6",
            "EHkDUkADkYnUY1cjCa5Lgc9qxLTMUQEBQm",
        }:
            return False
        response = self._makeUnauthenticatedCall(
            function=requests.get,
            endpoint='/proposals/admin')
        if response.status_code == 200:
            return address in response.json()
        return False

    def getUnapprovedProposals(self, address: str = None) -> dict:
        """Get unapproved proposals only if user has admin rights"""
        try:
            if not self.isApprovedAdmin(address):
                return {
                    'status': 'error',
                    'message': 'Unauthorized access'
                }

            response = self._makeUnauthenticatedCall(
                function=requests.get,
                endpoint='/proposals/unapproved'
            )

            if response.status_code == 200:
                return {
                    'status': 'success',
                    'proposals': response.json()
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Failed to fetch unapproved proposals'
                }

        except Exception as e:
            logging.error(f"Error in getUnapprovedProposals: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def approveProposal(self, address: str, proposal_id: int) -> tuple[bool, dict]:
        """Approve a proposal only if user has admin rights"""
        try:
            if not self.isApprovedAdmin(address):
                return False, {'error': 'Unauthorized access'}

            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint=f'/proposals/approve/{proposal_id}'
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {'error': f"Failed to approve proposal: {response.text}"}

        except Exception as e:
            return False, {'error': str(e)}

    def disapproveProposal(self, address: str, proposal_id: int) -> tuple[bool, dict]:
        """Disapprove a proposal only if user has admin rights"""
        try:
            if not self.isApprovedAdmin(address):
                return False, {'error': 'Unauthorized access'}

            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint=f'/proposals/disapprove/{proposal_id}'
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {'error': f"Failed to disapprove proposal: {response.text}"}

        except Exception as e:
            return False, {'error': str(e)}

    def getActiveProposals(self) -> dict:
        """
        Fetches active proposals
        """
        try:
            response = self._makeUnauthenticatedCall(
                function=requests.get,
                endpoint='/proposals/active'
            )
            if response.status_code == 200:
                return {'status': 'success', 'proposals': response.json()}
            else:
                error_message = f"Server returned status code {response.status_code}: {response.text}"
                return {'status': 'error', 'message': error_message}
        except Exception as e:
            error_message = f"Error in getActiveProposals: {str(e)}"
            return {'status': 'error', 'message': error_message}

    def submitProposalVote(self, proposal_id: int, vote: str) -> tuple[bool, dict]:
        """
        Submits a vote for a proposal
        """
        try:
            vote_data = {
                "proposal_id": int(proposal_id),  # Send proposal_id as integer
                "vote": str(vote),
            }
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/proposal/vote/submit',
                payload=vote_data  # Pass the vote_data dictionary directly
            )
            if response.status_code == 200:
                return True, response.text
            else:
                error_message = f"Server returned status code {response.status_code}: {response.text}"
                return False, {"error": error_message}

        except Exception as e:
            error_message = f"Error in submitProposalVote: {str(e)}"
            return False, {"error": error_message}

    def poolAccepting(self, status: bool) -> tuple[bool, dict]:
        """
        Function to set the pool status to accepting or not accepting
        """
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/stake/lend/enable' if status else '/stake/lend/disable')
            if response.status_code == 200:
                return True, response.text
            else:
                error_message = f"Server returned status code {response.status_code}: {response.text}"
                return False, {"error": error_message}
        except Exception as e:
            error_message = f"Error in poolAccepting: {str(e)}"
            return False, {"error": error_message}

    ## untested ##

    def setPoolWorkerReward(self, rewardPercentage: float) -> tuple[bool, dict]:
        """
        Function to set the pool status to accepting or not accepting
        """
        try:
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/pool/worker/reward/set',
                payload=json.dumps({"rewardPercentage": float(rewardPercentage)}))
            if response.status_code == 200:
                return True, response.text
            else:
                error_message = f"Server returned status code {response.status_code}: {response.text}"
                return False, {"error": error_message}
        except Exception as e:
            error_message = f"Error in poolAcceptingWorkers: {str(e)}"
            return False, {"error": error_message}

    def getPoolWorkerReward(self, address: str) -> tuple[bool, dict]:
        """
        Function to set the pool status to accepting or not accepting
        """
        try:
            response = self._makeUnauthenticatedCall(
                function=requests.get,
                endpoint=f'/pool/worker/reward/get/{address}')
            if response.status_code == 200:
                return True, response.text
            else:
                error_message = f"Server returned status code {response.status_code}: {response.text}"
                return False, {"error": error_message}
        except Exception as e:
            error_message = f"Error in poolAcceptingWorkers: {str(e)}"
            return False, {"error": error_message}

    def setMiningMode(self, status: bool) -> tuple[bool, dict]:
        """
        Function to set the worker mining mode
        """
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/worker/mining/mode/enable' if status else '/worker/mining/mode/disable')
            if response.status_code == 200:
                return True, response.text
            else:
                error_message = f"Server returned status code {response.status_code}: {response.text}"
                return False, {"error": error_message}
        except Exception as e:
            error_message = f"Error in setMiningMode: {str(e)}"
            return False, {"error": error_message}

    def getMiningMode(self, address) -> tuple[bool, dict]:
        """
        Function to set the worker mining mode
        """
        try:
            response = self._makeUnauthenticatedCall(
                function=requests.get,
                endpoint=f'/worker/mining/mode/get/{address}')
            if response.status_code == 200:
                return True, response.text
            else:
                error_message = f"Server returned status code {response.status_code}: {response.text}"
                return False, {"error": error_message}
        except Exception as e:
            error_message = f"Error in setMiningMode: {str(e)}"
            return False, {"error": error_message}

    def loopbackCheck(self, ipAddress:Union[str, None], port: Union[int, None]) -> tuple[bool, dict]:
        """
        asks the central server (could ask fellow Neurons) if our own dataserver
        is publically reachable.
        """
        try:
            response = self._makeUnauthenticatedCall(
                function=requests.post,
                endpoint='/api/v0/loopback/check',
                payload=json.dumps({
                    **({'ip': str(ipAddress)} if ipAddress is not None else {}),
                    **({'port': port} if port is not None else {})}))
            if response.status_code == 200:
                try:
                    return True, response.json().get('port_open', False)
                except Exception as e:
                    return False, {"unexpected error": e, "response.text": response.text}
            else:
                error_message = f"Server returned status code {response.status_code}: {response.text}"
                return False, {"error": error_message}
        except Exception as e:
            error_message = f"Error in setMiningMode: {str(e)}"
            return False, {"error": error_message}
