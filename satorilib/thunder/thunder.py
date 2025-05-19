''' Simple HTTP wrapper for the Thunder payment channel micro-service. '''

from typing import Dict, List, Optional, Union, Any, Callable
import requests
import logging

class ThunderClient:
    """Client for interacting with the Thunder payment channel microservice.
    
    This client provides a simple interface for all Thunder API endpoints.
    Authentication is handled separately by the caller.
    """
    
    def __init__(self, base_url: str = "http://localhost:5000", wallet = None):
        """Initialize the Thunder client.
        
        Args:
            base_url: Base URL of the Thunder service, defaults to http://localhost:5000
        """
        self.base = base_url.rstrip("/")
        self.wallet = wallet

    def _auth_headers(
        self, *, 
        pubkey: Union[str, None] = None, 
        address: Union[str, None] = None, 
        signature: Union[str, None] = None, 
        challenge: Union[str, None] = None,
    ):
        challenge = challenge or self.get_challenge().get('message')
        return {
            'message': challenge,
            'pubkey': pubkey or self.wallet.publicKey,
            'address': address or self.wallet.address,
            'signature': signature or self.wallet.sign(challenge).decode()}

    def _make_authenticated_call(
        self,
        function: Callable,
        endpoint: str,
        payload: Optional[Union[Dict, str]] = None,
        headers: Optional[Dict] = None,
        raise_for_status: bool = True,
    ) -> requests.Response:
        """Make an authenticated call to the Thunder API.
        
        Args:
            function: The requests function to call (get, post, etc)
            endpoint: The API endpoint to call
            payload: Optional JSON payload to send
            headers: Optional additional headers
            raise_for_status: Whether to raise on non-200 status codes
            
        Returns:
            The requests Response object
        """
        if isinstance(payload, dict):
            logging.info(
                f'outgoing: {endpoint}',
                str(payload)[:40] + ('...' if len(str(payload)) > 40 else ''),
                print=True)
            
        r = function(
            f"{self.base}{endpoint}",
            headers=headers or (self._auth_headers() if self.wallet is not None else {}),
            json=payload,
            timeout=10)
            
        if raise_for_status:
            try:
                r.raise_for_status()
            except requests.HTTPError as e:
                logging.error('authenticated server error:', r.text, e)
                raise
                
        logging.info(
            f'incoming: {endpoint}',
            r.text[:40] + ('...' if len(r.text) > 40 else ''),
            print=True)
        return r

    def _make_unauthenticated_call(
        self,
        function: Callable,
        endpoint: str,
        payload: Optional[Union[Dict, str]] = None,
        headers: Optional[Dict] = None,
    ) -> requests.Response:
        """Make an unauthenticated call to the Thunder API.
        
        Args:
            function: The requests function to call (get, post, etc)
            endpoint: The API endpoint to call
            payload: Optional JSON payload to send
            headers: Optional additional headers
            
        Returns:
            The requests Response object
        """
        if isinstance(payload, dict):
            logging.info(
                f'outgoing: {endpoint}',
                str(payload)[:40] + ('...' if len(str(payload)) > 40 else ''),
                print=True)
            
        r = function(
            f"{self.base}{endpoint}",
            headers=headers or {},
            json=payload,
            timeout=10)
            
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            logging.error('unauthenticated server error:', r.text, e)
            raise
            
        logging.info(
            f'incoming: {endpoint}',
            r.text[:40] + ('...' if len(r.text) > 40 else ''),
            print=True)
        return r

    def get_challenge(self) -> Dict[str, str]:
        """Get an authentication challenge from the server.
        
        Returns:
            Dict containing the challenge string
        """
        r = self._make_unauthenticated_call(requests.get, "/challenge")
        return r.json()

    def create_channel(self, *, redeem_script: str, sender_pubkey: str, 
                      receiver_pubkey: str, sender_address: str, 
                      receiver_address: str, funding_txid: str,
                      funding_vout: int, funding_value: int,
                      abs_timeout: int, p2sh_address: Optional[str] = None,
                      headers: Optional[Dict] = None) -> Dict[str, str]:
        """Create a new payment channel.
        
        Args:
            redeem_script: Hex-encoded redeem script
            sender_pubkey: Sender's public key
            receiver_pubkey: Receiver's public key
            sender_address: Sender's Evrmore address
            receiver_address: Receiver's Evrmore address
            funding_txid: Funding transaction ID
            funding_vout: Output index in funding transaction
            funding_value: Amount in satoshis
            abs_timeout: Absolute locktime
            p2sh_address: Optional P2SH address (will be derived if not provided)
            headers: Optional authentication headers
            
        Returns:
            Dict containing channel_id and p2sh_address
        """
        payload = {
            "redeem_script": redeem_script,
            "sender_pubkey": sender_pubkey,
            "receiver_pubkey": receiver_pubkey,
            "sender_address": sender_address,
            "receiver_address": receiver_address,
            "funding_txid": funding_txid,
            "funding_vout": funding_vout,
            "funding_value": funding_value,
            "abs_timeout": abs_timeout,
        }
        if p2sh_address:
            payload["p2sh_address"] = p2sh_address
            
        r = self._make_authenticated_call(requests.post, "/channel", 
                                        payload=payload, headers=headers)
        return r.json()

    def list_channels(self, headers: Optional[Dict] = None) -> Dict[str, List[str]]:
        """List all channels where the authenticated user is sender or receiver.
        
        Args:
            headers: Optional authentication headers
            
        Returns:
            Dict containing lists of channel IDs for both sender and receiver roles
        """
        r = self._make_authenticated_call(requests.get, "/channels", headers=headers)
        return r.json()

    def get_channel(self, channel_id: str, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """Get detailed information about a specific channel.
        
        Args:
            channel_id: ID of the channel to retrieve
            headers: Optional authentication headers
            
        Returns:
            Dict containing channel details
        """
        r = self._make_authenticated_call(requests.get, f"/channels/{channel_id}", 
                                        headers=headers)
        return r.json()

    def add_commitment(self, channel_id: str, *, partial_tx_hex: str,
                      pay_sats: int, remainder_sats: int,
                      headers: Optional[Dict] = None) -> Dict[str, str]:
        """Add or update a commitment for a channel.
        
        Args:
            channel_id: ID of the channel
            partial_tx_hex: Hex-encoded partial transaction
            pay_sats: Payment amount in satoshis
            remainder_sats: Remainder amount in satoshis
            headers: Optional authentication headers
            
        Returns:
            Dict containing the commitment ID
            
        Raises:
            requests.HTTPError: If channel is already claimed (450) or other errors
        """
        payload = {
            "partial_tx_hex": partial_tx_hex,
            "pay_sats": pay_sats,
            "remainder_sats": remainder_sats
        }
        r = self._make_authenticated_call(
            requests.post, 
            f"/channels/{channel_id}/commitment",
            payload=payload,
            headers=headers)
        return r.json()

    def get_latest_commitment(self, channel_id: str, 
                            headers: Optional[Dict] = None) -> Dict[str, Any]:
        """Get the latest commitment for a channel.
        
        Args:
            channel_id: ID of the channel
            headers: Optional authentication headers
            
        Returns:
            Dict containing commitment details
        """
        r = self._make_authenticated_call(
            requests.get,
            f"/channels/{channel_id}/commitments/latest",
            headers=headers)
        return r.json()

    def claim_commitment(self, channel_id: str, commitment_id: str, *,
                        claim_txid: Optional[str] = None,
                        claim_vout: Optional[int] = None,
                        headers: Optional[Dict] = None) -> Dict[str, Any]:
        """Claim a commitment for a channel.
        
        Args:
            channel_id: ID of the channel
            commitment_id: ID of the commitment to claim
            claim_txid: Optional transaction ID of the claim
            claim_vout: Optional output index of the claim
            headers: Optional authentication headers
            
        Returns:
            Dict containing claim details
        """
        payload = {}
        if claim_txid is not None:
            payload["claim_txid"] = claim_txid
        if claim_vout is not None:
            payload["claim_vout"] = claim_vout
            
        r = self._make_authenticated_call(
            requests.post,
            f"/channels/{channel_id}/commitments/{commitment_id}/claim",
            payload=payload,
            headers=headers)
        return r.json()