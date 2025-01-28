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
