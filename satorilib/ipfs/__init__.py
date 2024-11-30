'''
ipfs and ipns methods

logic looks like this: 
upon getting a stream id to evaluate, the client will ask the server for the ipns key by source, stream, target, and wallet.
the server will respond with a the ipfs and ipns keys.
side bar:
    if the client didn't care about the wallet id, it could just ask for the ipns key by source, stream, and target.
    the server would respond with a map of wallet ids and their associated the ipfs and ipns keys.
    the client will pick the one most popular for that stream and target, hopefully it matches the one for the walletid it's subscribing to.
    if not, perhaps it needs to get both and compare. if the wallet id one is a subset of the most popular one, it will use the most popular one. 
    if the most popular one is a subset of the wallet id one, it will use the wallet id one.
    if the wallet id one is not a subset of the most popular one, it will use the wallet id one.
it'll download the data and evaluate it.
if it decides to subscribe to the stream it will also notify the server of the ipns key and the ipfs key upon each observation.
when a client send a cid to the server, the server will tell the client that they are out of line if: 
    the stream does not have a stream_id and 
    the cid does not match the most popular or the cid it's replacing does not match the most popular.
'''
from .ipfs import Ipfs
