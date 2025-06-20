'''
this file and api_client.py were part of a half-baked attempt to standardize the API for the Satori server.
it was never completed.
'''

from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Generic, T
from datetime import datetime
from enum import Enum

# Base Models
class Wallet(BaseModel):
    address: str
    pubkey: Optional[str] = None
    alias: Optional[str] = None
    eth_address: Optional[str] = None

class Stream(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    publisher: Optional[str] = None
    subscribers: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Prediction(BaseModel):
    stream_id: int
    prediction: str
    timestamp: datetime
    wallet: Wallet

class Observation(BaseModel):
    stream_id: int
    observation: str
    timestamp: datetime
    wallet: Wallet
    centrifugo: bool = False

# Authentication Models
class AuthChallenge(BaseModel):
    challenge: str
    timestamp: datetime

class AuthResponse(BaseModel):
    signature: str
    pubkey: str
    timestamp: datetime

# Stream Management Models
class StreamRegistration(BaseModel):
    stream: Stream
    payload: Optional[str] = None

class StreamSubscription(BaseModel):
    stream_id: int
    wallet: Wallet
    payload: Optional[str] = None

class PinRegistration(BaseModel):
    pin: Dict[str, Any]
    payload: Optional[str] = None

# Voting Models
class ManifestVote(BaseModel):
    wallet: Wallet
    votes: Dict[str, int]

class SanctionVote(BaseModel):
    wallet: Wallet
    vault: Wallet
    votes: Dict[str, int]

# Mining and Staking Models
class MiningConfig(BaseModel):
    address: str
    mode: bool
    pool_size: Optional[float] = None
    worker_reward: Optional[float] = None

class StakingConfig(BaseModel):
    address: str
    amount: float
    proxy_address: Optional[str] = None
    charity_address: Optional[str] = None

class LendingConfig(BaseModel):
    parent_address: str
    child_address: str
    amount: float
    vault_address: Optional[str] = None

# Proposal Models
class ProposalStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    APPROVED = "approved"
    UNAPPROVED = "unapproved"

class Proposal(BaseModel):
    id: int
    title: str
    description: str
    proposer: Wallet
    status: ProposalStatus
    created_at: datetime
    expires_at: datetime
    votes: Optional[Dict[str, int]] = None

class ProposalVote(BaseModel):
    proposal_id: int
    wallet: Wallet
    vote: str  # "yes" or "no"

# Response Models
class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    status_code: int = 200

# API Endpoints
class Endpoints:
    # Authentication
    REGISTER_WALLET = "/register/wallet"
    LOGIN_WALLET = "/login/wallet"
    
    # Stream Management
    REGISTER_STREAM = "/register/stream"
    REMOVE_STREAM = "/remove/stream"
    RESTORE_STREAM = "/restore/stream"
    GET_STREAMS = "/get/streams"
    MY_STREAMS = "/my/streams"
    REQUEST_STREAM = "/request/stream"
    REQUEST_SPECIFIC_STREAM = "/request/stream/specific"
    FLAG_STREAM = "/flag/stream"
    
    # Predictions and Observations
    RECORD_PREDICTION = "/record/prediction"
    RECORD_OBSERVATION = "/record/observation"
    RECORD_PREDICTION_CENTRIFUGO = "/record/prediction/centrifugo"
    RECORD_OBSERVATION_CENTRIFUGO = "/record/observation/centrifugo"
    
    # Voting
    SUBMIT_MANIFEST_VOTE = "/submit/manifest/vote"
    SUBMIT_SANCTION_VOTE = "/submit/sanction/vote"
    REMOVE_SANCTION_VOTE = "/remove/sanction/vote"
    
    # Mining and Staking
    MINE_TO_ADDRESS = "/mine/to/address"
    STAKE_FOR_ADDRESS = "/stake/for/address"
    STAKE_PROXY_CHARITY = "/stake/proxy/charity"
    STAKE_PROXY_REMOVE = "/stake/proxy/remove"
    STAKE_CHECK = "/stake/check"
    
    # Lending
    LEND_TO_ADDRESS = "/stake/lend/to/address"
    LEND_REMOVE = "/stake/lend/remove"
    LEND_ADDRESS = "/stake/lend/address"
    
    # Proposals
    SUBMIT_PROPOSAL = "/proposal/submit"
    GET_PROPOSALS = "/proposals/get/all"
    GET_APPROVED_PROPOSALS = "/proposals/get/approved"
    APPROVE_PROPOSAL = "/proposals/approve/{proposal_id}"
    DISAPPROVE_PROPOSAL = "/proposals/disapprove/{proposal_id}"
    SUBMIT_PROPOSAL_VOTE = "/proposal/vote/submit"
    
    # Content Management
    CONTENT_CREATED = "/api/v0/content/created"
    DELETE_CONTENT = "/api/v0/content/delete"
    APPROVE_INVITERS = "/api/v0/inviters/approve"
    DISAPPROVE_INVITERS = "/api/v0/inviters/disapprove"
    
    # System Status
    CHECKIN = "/checkin"
    CHECKIN_CHECK = "/checkin/check"
    GET_BALANCES = "/api/v0/balances/get"
    GET_POWER_BALANCE = "/get/power/balance"