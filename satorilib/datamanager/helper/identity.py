from typing import Union
from abc import ABC, abstractmethod

class Identity(ABC):

    @property
    @abstractmethod
    def pubkey(self) -> str:
        """Returns the public key."""
        pass

    @property
    @abstractmethod
    def address(self) -> str:
        """Returns the address."""
        pass

    @abstractmethod
    def challenge(self) -> str:
        """Genergates a challenge for challenge response."""
        pass

    @abstractmethod
    def sign(self, msg: str) -> bytes:
        """Signs a message and returns the signature."""
        pass

    @abstractmethod
    def verify(self,
        msg: str,
        sig: bytes,
        address: Union[str, None] = None,
        pubkey: Union[str, bytes, None] = None,
    ) -> bool:
        """Verifies a message signature."""
        pass

    @abstractmethod
    def authenticationPayload(
        self,
        challengeId: Union[str, None] = None,
        challenged:Union[str, None] = None,
        signature:Union[bytes, None] = None,
    ) -> dict[str, str]:
        """
        {
            'pubkey': self.pubkey,
            'address': self.address,
            'challenge': self.challenge(),
        }
        """
        pass
