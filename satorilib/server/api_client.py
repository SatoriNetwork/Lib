'''
this file and spec.py were part of a half-baked attempt to standardize the API for the Satori server.
it was never completed.
'''
from typing import Optional, Dict, Any, TypeVar, Generic
import requests
from .spec import (
    Wallet, Stream, Prediction, Observation, 
    ApiResponse, Endpoints, AuthResponse,
    StreamRegistration, StreamSubscription,
    ManifestVote, SanctionVote, Proposal,
    ProposalVote, MiningConfig, StakingConfig,
    LendingConfig
)

T = TypeVar('T')

class SatoriApiClient:
    def __init__(self, base_url: str, wallet: Optional[Wallet] = None):
        self.base_url = base_url.rstrip('/')
        self.wallet = wallet
        self.session = requests.Session()

    def _make_request(
        self, 
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[type] = None
    ) -> ApiResponse[T]:
        url = f"{self.base_url}{endpoint}"
        
        # Add auth headers if wallet exists
        headers = {}
        if self.wallet:
            headers.update({
                'X-Wallet-Address': self.wallet.address,
                'X-Wallet-Pubkey': self.wallet.pubkey or '',
            })

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers
            )
            response.raise_for_status()
            
            # Parse response into model if provided
            if response_model:
                data = response_model.parse_obj(response.json())
            else:
                data = response.json()

            return ApiResponse(
                success=True,
                data=data,
                status_code=response.status_code
            )
        except requests.exceptions.RequestException as e:
            return ApiResponse(
                success=False,
                error=str(e),
                status_code=getattr(e.response, 'status_code', 500)
            )

    # Authentication Methods
    def register_wallet(self, wallet: Wallet) -> ApiResponse[Wallet]:
        return self._make_request(
            'POST',
            Endpoints.REGISTER_WALLET,
            data=wallet.dict(),
            response_model=Wallet
        )

    def login_wallet(self) -> ApiResponse[AuthResponse]:
        return self._make_request(
            'GET',
            Endpoints.LOGIN_WALLET,
            response_model=AuthResponse
        )

    # Stream Methods
    def register_stream(self, registration: StreamRegistration) -> ApiResponse[Stream]:
        return self._make_request(
            'POST',
            Endpoints.REGISTER_STREAM,
            data=registration.dict(),
            response_model=Stream
        )

    def get_streams(self) -> ApiResponse[List[Stream]]:
        return self._make_request(
            'GET',
            Endpoints.GET_STREAMS,
            response_model=List[Stream]
        )

    def my_streams(self) -> ApiResponse[List[Stream]]:
        return self._make_request(
            'GET',
            Endpoints.MY_STREAMS,
            response_model=List[Stream]
        )

    # Prediction and Observation Methods
    def record_prediction(self, prediction: Prediction) -> ApiResponse[Prediction]:
        return self._make_request(
            'POST',
            Endpoints.RECORD_PREDICTION,
            data=prediction.dict(),
            response_model=Prediction
        )

    def record_observation(self, observation: Observation) -> ApiResponse[Observation]:
        return self._make_request(
            'POST',
            Endpoints.RECORD_OBSERVATION,
            data=observation.dict(),
            response_model=Observation
        )

    # Voting Methods
    def submit_manifest_vote(self, vote: ManifestVote) -> ApiResponse[Dict[str, int]]:
        return self._make_request(
            'POST',
            Endpoints.SUBMIT_MANIFEST_VOTE,
            data=vote.dict()
        )

    def submit_sanction_vote(self, vote: SanctionVote) -> ApiResponse[Dict[str, int]]:
        return self._make_request(
            'POST',
            Endpoints.SUBMIT_SANCTION_VOTE,
            data=vote.dict()
        )

    # Mining and Staking Methods
    def set_mining_config(self, config: MiningConfig) -> ApiResponse[MiningConfig]:
        return self._make_request(
            'POST',
            Endpoints.MINE_TO_ADDRESS,
            data=config.dict(),
            response_model=MiningConfig
        )

    def stake_for_address(self, config: StakingConfig) -> ApiResponse[StakingConfig]:
        return self._make_request(
            'POST',
            Endpoints.STAKE_FOR_ADDRESS,
            data=config.dict(),
            response_model=StakingConfig
        )

    # Proposal Methods
    def submit_proposal(self, proposal: Proposal) -> ApiResponse[Proposal]:
        return self._make_request(
            'POST',
            Endpoints.SUBMIT_PROPOSAL,
            data=proposal.dict(),
            response_model=Proposal
        )

    def get_proposals(self) -> ApiResponse[List[Proposal]]:
        return self._make_request(
            'GET',
            Endpoints.GET_PROPOSALS,
            response_model=List[Proposal]
        )

    def submit_proposal_vote(self, vote: ProposalVote) -> ApiResponse[Dict[str, int]]:
        return self._make_request(
            'POST',
            Endpoints.SUBMIT_PROPOSAL_VOTE,
            data=vote.dict()
        ) 