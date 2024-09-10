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
from satorilib.api.time.time import timeToTimestamp
from satorilib.api.wallet import Wallet
from satorilib.concepts.structs import Stream
from satorilib.server.api import ProposalSchema, VoteSchema
from marshmallow import ValidationError


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
        json: Union[str, None] = None,
        challenge: str = None,
        useWallet: Wallet = None,
        extraHeaders: Union[dict, None] = None,
        raiseForStatus: bool = True,
    ) -> requests.Response:
        if json is not None:
            logging.info(
                'outgoing:',
                json[0:40], f'{"..." if len(json) > 40 else ""}',
                print=True)
        r = function(
            (url or self.url) + endpoint,
            headers={
                **(useWallet or self.wallet).authPayload(
                    asDict=True,
                    challenge=challenge or self._getChallenge()),
                **(extraHeaders or {}),
            },
            json=json)
        if raiseForStatus:
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logging.error('authenticated server err:',
                              r.text, e, color='red')
                r.raise_for_status()
        logging.info(
            'incoming:',
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
            json=self.wallet.registerPayload())

    def registerStream(self, stream: dict, payload: str = None):
        ''' publish stream {'source': 'test', 'name': 'stream1', 'target': 'target'}'''
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/register/stream',
            json=payload or json.dumps(stream))

    def registerSubscription(self, subscription: dict, payload: str = None):
        ''' subscribe to stream '''
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/register/subscription',
            json=payload or json.dumps(subscription))

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
            json=payload or json.dumps(pin))

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
            json=payload or json.dumps(stream))

    def myStreams(self):
        ''' subscribe to primary data stream and and publish prediction '''
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/my/streams',
            json='{}')

    def removeStream(self, stream: dict = None, payload: str = None):
        ''' removes a stream from the server '''
        if payload is None and stream is None:
            raise ValueError('stream or payload must be provided')
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/remove/stream',
            json=payload or json.dumps(stream or {}))

    def checkin(self, referrer: str = None) -> dict:
        challenge = self._getChallenge()
        response = self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/checkin',
            json=self.wallet.registerPayload(challenge=challenge),
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
            json=self.wallet.registerPayload(challenge=challenge),
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
        # TODO: when we implement a split in the server /votes_for/manifest
        #       might be on the website domain, along with others (that don't
        #       require authentication) so we will have to handle that.
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

    def submitMaifestVote(self, wallet: Wallet, votes: dict[str, int]):
        # todo authenticate the vault instead
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/vote_on/manifest',
            useWallet=wallet,
            json=json.dumps(votes or {})).text

    def submitSanctionVote(self, wallet: Wallet, votes: dict[str, int]):
        return self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/vote_on/sanction',
            useWallet=wallet,
            json=json.dumps(votes or {})).text

    def removeSanctionVote(self, wallet: Wallet):
        return self._makeAuthenticatedCall(
            function=requests.Get,
            endpoint='/clear_votes_on/sanction',
            useWallet=wallet).text

    def pinDepinStream(self, stream: dict = None) -> tuple[bool, str]:
        ''' removes a stream from the server '''
        if stream is None:
            raise ValueError('stream must be provided')
        response = self._makeAuthenticatedCall(
            function=requests.post,
            endpoint='/register/subscription/pindepin',
            json=json.dumps(stream))
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

    def mineToAddress(
        self,
        vaultSignature: Union[str, bytes],
        vaultPubkey: str,
        address: str
    ) -> tuple[bool, str]:
        ''' set reward address '''
        try:
            if isinstance(vaultSignature, bytes):
                vaultSignature = vaultSignature.decode()
            js = json.dumps({
                'vaultSignature': vaultSignature,
                'vaultPubkey': vaultPubkey,
                'address': address})
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/mine/to/address',
                json=js)
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
                json=json.dumps({
                    'vaultSignature': vaultSignature,
                    'vaultPubkey': vaultPubkey,
                    'address': address}))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to determine status of mine to address feature due to connection timeout; try again Later.', e, color='yellow')
            return False, ''

    def reportVault(
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
                endpoint='/vault/report',
                json=json.dumps({
                    'walletSignature': walletSignature,
                    'vaultSignature': vaultSignature,
                    'vaultPubkey': vaultPubkey,
                    'address': address}))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to enable status of Mine-To-Vault feature due to connection timeout; try again Later.', e, color='yellow')
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
                json=json.dumps({
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
                json=json.dumps({
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

    def ticketApplication(self, tx: str) -> bool:
        ''' gets wallet stats '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint=f'/ticket/application/{tx}')
            if response.text in ('OK', 'OK, ALREADY EXISTS'):
                return True
        except Exception as e:
            logging.warning(
                'unable to disable status of Mine-To-Vault feature due to connection timeout; try again Later.', e, color='yellow')
        # if response.text in ('INVALID TX', 'FAILED'):
        return False

    def ticketCheck(self) -> bool:
        ''' gets wallet stats '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/ticket/check')
            if response.text in ('True', 'Probably'):
                return True
        except Exception as e:
            logging.warning(
                'unable to disable status of Mine-To-Vault feature due to connection timeout; try again Later.', e, color='yellow')
            return False
        return False

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

    def betaStatus(self) -> tuple[bool, dict]:
        ''' removes a stream from the server '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.get,
                endpoint='/beta/status')
            return response.status_code < 400, response.json()
        except Exception as e:
            logging.warning(
                'unable to get beta status due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def betaClaim(self, ethAddress: str) -> tuple[bool, dict]:
        ''' removes a stream from the server '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/beta/claim',
                json=json.dumps({'ethAddress': ethAddress}))
            return response.status_code < 400,  response.json()
        except Exception as e:
            logging.warning(
                'unable to claim beta due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

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
                json=json.dumps({'child': address, 'childId': childId}))
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
                json=json.dumps({'child': address, 'childId': childId}))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to stakeProxyCharityNot due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def stakeProxyRequest(self, address: str) -> tuple[bool, dict]:
        ''' removes a stream from the server '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/stake/proxy/request',
                json=json.dumps({'parent': address}))
            print(response.status_code < 400, response.text)
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to stakeProxyRequest due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def stakeProxyApprove(self, address: str, childId: int) -> tuple[bool, dict]:
        ''' removes a stream from the server '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/stake/proxy/approve',
                json=json.dumps({'child': address, 'childId': childId}))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to stakeProxyApprove due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def stakeProxyDeny(self, address: str, childId: int) -> tuple[bool, dict]:
        ''' removes a stream from the server '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/stake/proxy/deny',
                json=json.dumps({'child': address, 'childId': childId}))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to stakeProxyDeny due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    def stakeProxyRemove(self, address: str, childId: int) -> tuple[bool, dict]:
        ''' removes a stream from the server '''
        try:
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/stake/proxy/remove',
                json=json.dumps({'child': address, 'childId': childId}))
            return response.status_code < 400, response.text
        except Exception as e:
            logging.warning(
                'unable to stakeProxyRemove due to connection timeout; try again Later.', e, color='yellow')
            return False, {}

    
    def getProposals(self):
        """
        Function to get all proposals by calling the API endpoint.
        """
        try:
            response = self._makeUnauthenticatedCall(
                function=requests.get,
                endpoint='/proposals'
            )
            if response.status_code == 200:
                # Fetch JSON data from the response
                response_data = response.json()

                # Load proposals using the schema
                proposals = ProposalSchema(many=True).load(response_data)
                return proposals
            else:
                print(f"Failed to get proposals. Status code: {response.status_code}")
                return []
        except requests.RequestException as e:
            print(f"Error occurred while fetching proposals: {str(e)}")
            return []

    def submitProposalVote(self, wallet: Wallet, proposal_id, vote):
        """
        Function to submit a vote by calling the API endpoint.
        """
        try:
            vote_data = VoteSchema().dump({"proposal_id": str(proposal_id), "vote": vote == 'yes'})
            response = self._makeAuthenticatedCall(
                function=requests.post,
                endpoint='/proposals_votes',
                json=vote_data)
            if response.status_code == 200:
                updated_proposal = response.json().get('proposal')
                if updated_proposal:
                    return True, updated_proposal
                else:
                    return False, "No updated proposal data received"
            else:
                return False, f"Failed to submit vote. Status code: {response.status_code}"
        except ValidationError as ve:
            return False, f"Validation error: {str(ve)}"
        except requests.RequestException as e:
            return False, f"Error occurred while submitting vote: {str(e)}"
        

    def testConnection(self):
        """
        Function to test the API connection by calling the test endpoint.
        """
        try:
            response = self._makeUnauthenticatedCall(
                function=requests.get,
                endpoint='/test')
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"Test failed. Status code: {response.status_code}"
        except requests.RequestException as e:
            return False, f"Error occurred while testing connection: {str(e)}"
