from typing import List, Tuple, Optional, Dict
from evrmore.wallet import CEvrmoreSecret
from evrmore.core.script import CScript, OP_0
from evrmore.core import CMutableTransaction
from satorilib.wallet.evrmore.utils.sign import signForPubkey


def multisig2Of2(
    *,
    tx: CMutableTransaction,
    vin_index: int,
    redeem_script: CScript,
    sighash_flag: int,
    pubkeys_in_script_order: Tuple[bytes, bytes],
    # supply any subset; we’ll only sign those we have
    keyring: Dict[bytes, CEvrmoreSecret],
    # already-collected cosigner sigs, map pubkey->sig (DER+flag)
    cosigner_sigs: Optional[Dict[bytes, bytes]] = None,
    # booleans/selectors to prepend (e.g., inner/outer IFs)
    prefix_booleans: Optional[List[int]] = None,  # e.g. [OP_TRUE, OP_FALSE]
) -> List[object]:
    """
    Returns: [OP_0, sig_for_pk0, sig_for_pk1, ...prefix_booleans...]
    in the exact order CHECKMULTISIG expects.
    """
    k0, k1 = pubkeys_in_script_order
    sigs_by_pk = dict(cosigner_sigs or {})

    # Create local signatures where possible
    for pk in (k0, k1):
        if pk not in sigs_by_pk and pk in keyring:
            sigs_by_pk[pk] = signForPubkey(keyring[pk], tx, vin_index, redeem_script, sighash_flag)

    # IMPORTANT: do NOT sort signatures. Order must match pubkey order in the redeem script.
    try:
        s0 = sigs_by_pk[k0]
        s1 = sigs_by_pk[k1]
    except KeyError:
        raise ValueError("Missing required signatures for 2-of-2 path.")

    elems: List[object] = [OP_0, s0, s1]  # dummy first, then sigs in pubkey order
    if prefix_booleans:
        elems.extend(prefix_booleans)  # e.g., [OP_TRUE, OP_FALSE] appended after sigs, but remember LIFO at execution
    return elems



