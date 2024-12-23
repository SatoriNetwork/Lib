import hashlib
import random
import time
from collections import defaultdict, deque

# For signatures, you'll need 'cryptography' or a similar library.
# pip install cryptography
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.exceptions import InvalidSignature

class Event:
    """
    An event with:
      - creator: node name that created the event
      - payload: data payload
      - parents: references to parent event IDs
      - timestamp: creation time
      - signature: cryptographic signature over the event hash
      - event_id: unique SHA-256 ID of the event
    """
    def __init__(self, creator, payload, parents=None, signature=None):
        self.creator = creator
        self.payload = payload
        self.parents = parents if parents else []
        self.timestamp = time.time()
        self.signature = signature
        self.event_id = None

    def compute_hash(self):
        """
        Compute a robust cryptographic hash for the event using SHA-256.
        The hash includes:
          - creator
          - payload
          - timestamp
          - sorted parent IDs
        """
        sorted_parents = ",".join(sorted(self.parents))
        data = f"{self.creator}:{self.payload}:{self.timestamp}:{sorted_parents}"
        return hashlib.sha256(data.encode("utf-8")).digest()

    def finalize(self, computed_hash: bytes = None):
        """
        Once we have the signature, we finalize the event_id as the hex of the hash + signature check.
        Reproducibility isn't required so we embed the signature check to ensure
        uniqueness, so we can't sign the same payload multiple times differently.
        """
        if not self.signature:
            raise ValueError("Cannot finalize event without a signature.")
        computed_hash = computed_hash or self.compute_hash()
        m = hashlib.sha256()
        m.update(computed_hash + self.signature)
        self.event_id = m.hexdigest()


class Node:
    """
    Each Node holds:
      - a local DAG of events (event_id -> Event)
      - a queue of orphaned events waiting for parents
      - a key pair (ECDSA) to sign new events
      - a list of peers for gossip
    """
    def __init__(self, name):
        self.name = name
        self.events = {}          # event_id -> Event
        self.orphan_queue = deque()  # events that reference missing parents
        self.peers = []

        # Create an ECDSA key pair
        self._private_key = ec.generate_private_key(ec.SECP256R1())
        self._public_key = self._private_key.public_key()

    def public_key_bytes(self):
        """
        For demonstration, you could share this with other nodes so they
        know how to verify your signatures. In an actual system, you'd
        distribute these via a certificate or config.
        """
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo)

    def create_event(self, payload):
        """
        Create a new event referencing the last 2 known event IDs.
        Sign the event, finalize the ID, store it in self.events.
        """
        known_events = list(self.events.keys())
        parents = known_events[-2:] if len(known_events) >= 2 else known_events
        event = Event(creator=self.name, payload=payload, parents=parents)

        # Sign the event
        message_digest = event.compute_hash()
        signature = self._private_key.sign(message_digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        event.signature = signature

        # finalize the event
        event.finalize(message_digest)

        # store it
        self.events[event.event_id] = event
        print(f"[{self.name}] Created event {event.event_id} with payload: '{payload}'")
        return event

    def merge_events(self, remote_events, public_key_map):
        """
        Merge remote events into our local DAG.
        - Validate each event's signature using the creator's public key.
        - Ensure we don't store duplicates or invalid events.
        - If an event references unknown parents, place it in the orphan queue.
          We'll attempt to resolve orphans each time we merge.
        """
        for e_id, event in remote_events.items():
            if e_id in self.events:
                # Already have it
                continue

            if not self.validate_event(event, public_key_map):
                print(f"[{self.name}] Rejected event {e_id} from {event.creator} (invalid signature).")
                continue

            # If the parents are known or empty, we can store it directly.
            # Otherwise, it's an orphan; store in orphan_queue for later resolution.
            missing_parents = [p for p in event.parents if p not in self.events]
            if missing_parents:
                print(f"[{self.name}] Found orphan event {e_id}; missing parents: {missing_parents}")
                self.orphan_queue.append(event)
            else:
                self.events[e_id] = event
                print(f"[{self.name}] Merged valid event {e_id} from {event.creator}.")

        # Attempt to resolve orphan events
        self.resolve_orphans()

    def resolve_orphans(self):
        """
        Try to integrate orphan events whose parents have since arrived.
        """
        resolved_any = True
        while resolved_any:
            resolved_any = False
            new_queue = deque()
            while self.orphan_queue:
                event = self.orphan_queue.popleft()
                missing_parents = [p for p in event.parents if p not in self.events]
                if missing_parents:
                    # still missing
                    new_queue.append(event)
                else:
                    # we can now merge it
                    self.events[event.event_id] = event
                    resolved_any = True
                    print(f"[{self.name}] Resolved orphan event {event.event_id} from {event.creator}")
            self.orphan_queue = new_queue

    def validate_event(self, event, public_key_map):
        """
        Verify the event's signature using the creator's public key
        (retrieved from public_key_map).
        """
        if event.creator not in public_key_map:
            # We don't know this node's public key, so we can't validate.
            # In a real system, you'd fetch it from some PKI or config.
            return False

        creator_pubkey = public_key_map[event.creator]
        # Recompute the base hash
        base_hash = event.compute_hash()
        try:
            creator_pubkey.verify(
                event.signature,
                base_hash,
                ec.ECDSA(utils.Prehashed(hashes.SHA256())))
            return True
        except InvalidSignature:
            return False

    def gossip(self, public_key_map):
        """
        Send all local events to a random peer.
        In a real system, you'd only send new events since last gossip, etc.
        """
        if not self.peers:
            return
        peer = random.choice(self.peers)
        # Construct a dict of event_id -> event for all local events
        peer.merge_events(self.events, public_key_map)
        print(f"[{self.name}] Gossiped {len(self.events)} events to {peer.name}.")

    def __repr__(self):
        return f"Node({self.name})"


def connect_nodes(nodes):
    """
    Connect each node to all the others (fully connected for simplicity).
    """
    for node in nodes:
        node.peers = [n for n in nodes if n != node]


def build_public_key_map(nodes):
    """
    Build a dictionary of node_name -> public_key object so that
    each node can validate events from each other node.
    """
    public_key_map = {}
    for node in nodes:
        # Load the public key object from the node
        pub_bytes = node.public_key_bytes()
        public_key = serialization.load_pem_public_key(pub_bytes)
        public_key_map[node.name] = public_key
    return public_key_map


def main():
    # create some nodes
    nodeA = Node("A")
    nodeB = Node("B")
    nodeC = Node("C")
    nodes = [nodeA, nodeB, nodeC]
    connect_nodes(nodes)

    # So each node can validate events from each other,
    # we build a global public_key_map that they share.
    # In a real system, each node might have its own store of known public keys,
    # but here we just do a simple global dict for demonstration.
    public_key_map = build_public_key_map(nodes)

    # each node creates an event
    for node in nodes:
        node.create_event(payload=f"Initial event from {node.name}")

    # do some gossip rounds
    for _ in range(5):
        random.choice(nodes).gossip(public_key_map)

    # each node makes another event
    for node in nodes:
        node.create_event(payload=f"Another event from {node.name}")

    # more gossip
    for _ in range(5):
        random.choice(nodes).gossip(public_key_map)

    # see final counts
    for node in nodes:
        print(f"[{node.name}] sees {len(node.events)} total events in its DAG.")

    for node in nodes:
        for event in node.events.values():
            print(f"[{node.name}] Event {event.event_id} has parents: {event.parents}")

if __name__ == "__main__":
    main()
