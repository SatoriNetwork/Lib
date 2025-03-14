class SDR():
    '''
    Semantic Representations
    are bit strings that represent the semantic meaning of the data.
    they encode a model of the data.
    each bit represents a specific property of the data.
    the properties are generally aranged from most significant to least,
    or from most general to least, or from largest population to smallest,
    or from most stable to most variable.
    typically holding a number of bits that are powers of 2.
    somestimes the last number of bits are reserved for a uid of the thing
    being represented incase it's categories match perfectly with any other rep.
    the more defined the semantic representation of the space (the more
    categories), the fewer uid bits are needed. sdrs can be of any length but if
    they are long enough they can be SSDRs or Sparse Semantically Distributed
    Representations. Sparse means most of the bits are zero, giving a high
    likelihood that a collision will never occur. For example a SSDR might be
    2048 bits of which only 40 bits are turned on or about 2%.

    if two representations are identical, they are the same thing.
    if two representations share bits, they are the similar.
    if two representations share some of the first bits, they are in the same
    very broad categories.
    if two representations share some of the last bits (other than the uid
    section), they share in some niche categories.
    if only the category bits are used, we are referencing the category itself.
    if all the count bits are used, we are not defining a specific chain, but an
    undefined chain in that category because there's no room left for it, that
    is, we are saying "unknown entity within this category."
    '''
    def __init__(self, bits: int, categories: list[str] = [], uid: int = 0):
        self.bits = bits
        self.categories = categories
        self.uid = uid

    def example():
        '''
        supported bridge chains - this is as yet unused - but we'll need it if
        we bridge any where else because the chain name is used in the evr memo
        and the integer is used in the bridgeBurn transact of the ethereum
        contract, so we need a mapping between the two somewhere. here we
        semantically encode the chains with 16-bits. if only the first 11 bits
        are used, we are defining the category itself, using the count portion
        we define the specific chain of that category, likewise, if all the
        count bits are used, we are not defining a specific chain, but an
        undefined chain in that category because there's no room left for it.
        0. Permissionless
        1. Permissioned
        2. UTXO-based
        3. Account-based
        4. Proof of Work
        5. Proof of Stake
        6. DAG based
        7. Smart Contract Support
        8. EVM Compatible
        9. Layer 1
        10. Native Privacy
        11. count
        12. count
        13. count
        14. count
        15. count
        '''
        return {
            'ethereum': 0b1001010111000001,
            'base': 0b1001010110000001,
            'evrmore': 0b1010100001000001,
        }

## though I like the idea of semantically encoding the our categories as a
## general rule, for what is development but a model fo the domain, it's not
## worth the effort to maintain the added complexity.
##
## v1 ##########################################################################
#
#from dataclasses import dataclass, field
#from typing import List
#
#@dataclass
#class SDR:
#    bits: int = 0
#    categories: List[str] = field(default_factory=list)
#    uid: int = 0
#
#    def get_bit(self, position: int) -> bool:
#        return ((self.bits >> position) & 1) == 1
#
#    def set_bit(self, position: int, value: bool) -> None:
#        if value:
#            self.bits |= (1 << position)
#        else:
#            self.bits &= ~(1 << position)
#
#
#@dataclass
#class SecurityPolicy(SDR):
#    """
#    A specialized SDR that encodes security policy toggles.
#    """
#
#    @property
#    def local_authentication(self) -> bool:
#        return self.get_bit(0)
#
#    @local_authentication.setter
#    def local_authentication(self, value: bool):
#        self.set_bit(0, value)
#
#    @property
#    def peer_authentication(self) -> bool:
#        return self.get_bit(1)
#
#    @peer_authentication.setter
#    def peer_authentication(self, value: bool):
#        self.set_bit(1, value)
#
#    @property
#    def local_encryption(self) -> bool:
#        return self.get_bit(2)
#
#    @local_encryption.setter
#    def local_encryption(self, value: bool):
#        self.set_bit(2, value)
#
#    @property
#    def peer_encryption(self) -> bool:
#        return self.get_bit(3)
#
#    @peer_encryption.setter
#    def peer_encryption(self, value: bool):
#        self.set_bit(3, value)
#
#
#if __name__ == "__main__":
#    policy = SecurityPolicy()
#    policy.local_authentication = True
#    policy.peer_authentication = True
#    policy.local_encryption = False
#    policy.peer_encryption = True
#
#    print("Bits (binary):", bin(policy.bits))
#    print("Local Auth:", policy.local_authentication)
#    print("Peer Auth:", policy.peer_authentication)
#    print("Local Encryption:", policy.local_encryption)
#    print("Peer Encryption:", policy.peer_encryption)
#
#
## v2 ##########################################################################
#
#from dataclasses import dataclass, field
#from typing import Dict, List, Union
#from enum import Enum
#
#class SecurityCategories(Enum):
#    LOCAL_AUTHENTICATION = 0
#    PEER_AUTHENTICATION = 1
#    LOCAL_ENCRYPTION = 2
#    PEER_ENCRYPTION = 3
#
#@dataclass
#class SDRv2:
#    """
#    An SDR that stores a general `bits` field and a mapping
#    from category -> bit position. The category can be a string
#    or an enum member, whichever you prefer.
#    """
#    bits: int = 0
#
#    # A dictionary mapping category-name -> bit position
#    # e.g. {"local_authentication": 0, "peer_authentication": 1, ...}
#    category_positions: Dict[str, int] = field(default_factory=dict)
#
#    # For demonstration—still optional—if you want to keep track
#    # of the categories in some list form:
#    categories: List[str] = field(default_factory=list)
#
#    def register_categories(self, cats: Union[List[str], type(Enum)]) -> None:
#        """
#        Populate or extend the category_positions dictionary
#        given either a list of strings or an Enum.
#        Each new category gets the next available bit position
#        if it's not already present.
#        """
#        if isinstance(cats, list):
#            for cat in cats:
#                if cat not in self.category_positions:
#                    next_bit = len(self.category_positions)
#                    self.category_positions[cat] = next_bit
#                    self.categories.append(cat)
#        elif issubclass(cats, Enum):
#            for member in cats:
#                cat_name = member.name  # or str(member) if you prefer
#                if cat_name not in self.category_positions:
#                    self.category_positions[cat_name] = member.value
#                    self.categories.append(cat_name)
#        else:
#            raise TypeError("cats must be a list of strings or an Enum class")
#
#    def get_bit_by_name(self, category: str) -> bool:
#        if category not in self.category_positions:
#            raise ValueError(f"Unknown category: {category}")
#        pos = self.category_positions[category]
#        return ((self.bits >> pos) & 1) == 1
#
#    def set_bit_by_name(self, category: str, value: bool) -> None:
#        if category not in self.category_positions:
#            raise ValueError(f"Unknown category: {category}")
#        pos = self.category_positions[category]
#        if value:
#            self.bits |= (1 << pos)
#        else:
#            self.bits &= ~(1 << pos)
#
#    def get_bit(self, cat: Union[str, Enum]) -> bool:
#        """
#        Convenient one-liner: pass either a string or an Enum member.
#        """
#        if isinstance(cat, Enum):
#            return self.get_bit_by_name(cat.name)
#        elif isinstance(cat, str):
#            return self.get_bit_by_name(cat)
#        else:
#            raise TypeError("cat must be a string or an Enum member")
#
#    def set_bit(self, cat: Union[str, Enum], value: bool) -> None:
#        """
#        Convenient one-liner: pass either a string or an Enum member.
#        """
#        if isinstance(cat, Enum):
#            self.set_bit_by_name(cat.name, value)
#        elif isinstance(cat, str):
#            self.set_bit_by_name(cat, value)
#        else:
#            raise TypeError("cat must be a string or an Enum member")
#
#
## Example usage:
#if __name__ == "__main__":
#    # Create a fresh SDR with no known categories:
#    my_sdr = SDR()
#
#    # Register an enum (SecurityCategories) so we know which bit goes to which category
#    my_sdr.register_categories(SecurityCategories)
#
#    # Now set some bits by passing Enum members
#    my_sdr.set_bit(SecurityCategories.LOCAL_AUTHENTICATION, True)
#    my_sdr.set_bit(SecurityCategories.PEER_AUTHENTICATION, True)
#    my_sdr.set_bit(SecurityCategories.LOCAL_ENCRYPTION, False)
#    my_sdr.set_bit(SecurityCategories.PEER_ENCRYPTION, True)
#
#    # Read them back
#    print("Bits (binary):", bin(my_sdr.bits))
#    print("Local Auth:", my_sdr.get_bit(SecurityCategories.LOCAL_AUTHENTICATION))
#    print("Peer Auth:", my_sdr.get_bit(SecurityCategories.PEER_AUTHENTICATION))
#    print("Local Encryption:", my_sdr.get_bit(SecurityCategories.LOCAL_ENCRYPTION))
#    print("Peer Encryption:", my_sdr.get_bit(SecurityCategories.PEER_ENCRYPTION))
#
#    # We can also register new categories by name, if needed:
#    my_sdr.register_categories(["some_new_flag", "another_flag"])
#    my_sdr.set_bit("some_new_flag", True)
#    print("New categories -> category_positions:", my_sdr.category_positions)
#    print("Bits (binary):", bin(my_sdr.bits))
