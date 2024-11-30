'''
https://docs.ipfs.tech/reference/kubo/rpc/#getting-started
https://github.com/lastmeta/Satori/issues/43

model: the client will pin the entire history, long term and 
recent term storage history, of the streams they subscribe 
to and the streams they publish.

they will add these ipfs pins to the ipns as well. to that
end they will generate a key for each stream they subscribe
to and each they publish.

https://docs.ipfs.tech/concepts/ipns/#example-ipns-setup-with-cli

we will make a table in the database called pins:
- wallet_id
- stream_id
- target_id
- ipns_key
- ipfs_key

the client will tell the server all of it's ipns keys when
it subscribes to a stream and it will remove the record from
the server when it unsubscribes.

when a client wants the entire history of a stream they will
ask the server for the ipns and the server will provide all
the ipns_keys for that stream_id-target_id

the client will pull one or more of them to evaluate it. if
the client pulls multiple it will keep the longest one - that
is the one that is most likely still active. it will report
inactive ones to the server who will remove them unless it's
the only one left for that stream_id target_id, it may do a
comparison itself just to be safe.

after the evalutation it will download it again to make sure 
it got the most recent data, and subscribe to the stream.

To do list:
1. clean up wallet table:
    - id,
    - address
    - pubkey
    - user_id
2. enforce 1-1 relationship for wallet to devices
3. create pins table
    - wallet_id
    - stream_id
    - target_id
    - ipns_key
    
4. create flow for saving ipfs
    - upon subscription to a stream the client will provide the ipns key to the server
    - upon publishing a stream the client will provide the ipns key to the server
5. create functions for ipfs needs
6. integrate functions into flows
    - subscribing process
    - evaluating process
    - etc.
7. server stuff.
'''

import requests
import simplejson


def baseUrl():
    return 'http://127.0.0.1:5001'


def apiVersion():
    return 'api/v0'


def validateEndpoints(x):
    return x if x in [
        'add',
        'bitswap/ledger',
        'bitswap/reprovide',
        'bitswap/stat',
        'bitswap/wantlist',
        'block/get',
        'block/put',
        'block/rm',
        'block/stat',
        'bootstrap',
        'bootstrap/add',
        'bootstrap/add/default',
        'bootstrap/list',
        'bootstrap/rm',
        'bootstrap/rm/all',
        'cat',
        'cid/base32',
        'cid/bases',
        'cid/codecs',
        'cid/format',
        'cid/hashes',
        'commands',
        'commands/completion/bash',
        'config',
        'config/edit',
        'config/profile/apply',
        'config/replace',
        'config/show',
        'dag/export',
        'dag/get',
        'dag/import',
        'dag/put',
        'dag/resolve',
        'dag/stat',
        'dht/query',
        'diag/cmds',
        'diag/cmds/clear',
        'diag/cmds/set-time',
        'diag/profile',
        'diag/sys',
        'files/chcid',
        'files/cp',
        'files/flush',
        'files/ls',
        'files/mkdir',
        'files/mv',
        'files/read',
        'files/rm',
        'files/stat',
        'files/write',
        'filestore/dups',
        'filestore/ls',
        'filestore/verify',
        'get',
        'id',
        'key/export',
        'key/gen',
        'key/import',
        'key/list',
        'key/rename',
        'key/rm',
        'key/rotate',
        'log/level',
        'log/ls',
        'ls',
        'multibase/decode',
        'multibase/encode',
        'multibase/list',
        'multibase/transcode',
        'name/publish',
        'name/resolve',
        'pin/add',
        'pin/ls',
        'pin/remote/add',
        'pin/remote/ls',
        'pin/remote/rm',
        'pin/remote/service/add',
        'pin/remote/service/ls',
        'pin/remote/service/rm',
        'pin/rm',
        'pin/update',
        'pin/verify',
        'ping',
        'refs',
        'refs/local',
        'repo/gc',
        'repo/migrate',
        'repo/stat',
        'repo/verify',
        'repo/version',
        'resolve',
        'routing/findpeer',
        'routing/findprovs',
        'routing/get',
        'routing/provide',
        'routing/put',
        'shutdown',
        'stats/bitswap',
        'stats/bw',
        'stats/dht',
        'stats/provide',
        'stats/repo',
        'swarm/addrs',
        'swarm/addrs/listen',
        'swarm/addrs/local',
        'swarm/connect',
        'swarm/disconnect',
        'swarm/filters',
        'swarm/filters/add',
        'swarm/filters/rm',
        'swarm/peering/add',
        'swarm/peering/ls',
        'swarm/peering/rm',
        'swarm/peers',
        'update',
        'version',
        'version/deps',
        # Experimental RPC commands
        'log/tail',
        'mount',
        'name/pubsub/cancel',
        'name/pubsub/state',
        'name/pubsub/subs',
        'p2p/close',
        'p2p/forward',
        'p2p/listen',
        'p2p/ls',
        'p2p/stream/close',
        'p2p/stream/ls',
        'pubsub/ls',
        'pubsub/peers',
        'pubsub/pub',
        'pubsub/sub',
        'swarm/limit',
        'swarm/stats',] else ''


def endpointStructures():
    return {
        'files/ls': {'Entries': [{'Name': str, 'Type': int, 'Size': int, 'Hash': str}]}}


def args(map):
    '''curl -X POST "http://127.0.0.1:5001/api/v0/swarm/disconnect?arg=/ip4/54.93.113.247/tcp/48131/p2p/QmUDS3nsBD1X4XK5Jo836fed7SErTyTuQzRqWaiQAyBYMP"'''
    if map:
        return '?' + '&'.join([f'{k}={v}' for k, v in map.items()])
    return ''


def call(endpoint, kwargs=None, headers=None, payload=None):
    # headers={
    #        'x-api-key': os.environ.get('INSIGHT_REPORT_KEY', ''),
    #        'Content-Type': 'application/json'},
    #    data=payload)
    r = requests.post(
        url='/'.join([baseUrl(), apiVersion(), endpoint]) + args(kwargs or {}),
        headers=headers,
        files=payload)
    r.raise_for_status()  # if 200 <= r.status_code <= 204:
    # requests.exceptions.ConnectionError try again
    try:
        return r.json()
    except simplejson.errors.JSONDecodeError:
        return r.text

# call(
#    endpoint=validateEndpoints('files/ls'),
#    kwargs={'long':True})
# call(
#    endpoint=validateEndpoints('filestore/ls'),
#    kwargs={'long':True})
#
#
# this is giving me so much trouble why not just use the shell?
# ipfs files cp /ipfs/$(ipfs add -r -Q <local-folder>) "/<dest-name>"
# call(
#    endpoint=validateEndpoints('add'),
#    kwargs={'pin':True, 'nocopy':True, },
#    #files={'path': 'C:\pin'}
#    )


def interpret(endpoint, response, extra=None):
    '''
    {'Entries': 
        [{'Name': 'moontree.json', 'Type': 0, 'Size': 58, 'Hash': 'QmcVwukinT7BdC2u9PqyZRFG1dheebQGaBzgytJF6NZD9M'}, 
        {'Name': 'moontree_logo.png', 'Type': 0, 'Size': 38414, 'Hash': 'QmXe1VJjmBi1Tjti8mUa2UyScvEPyUnhSGSZzwD19kCYUm'}]}
    '''
    if endpoint == 'files/ls':
        return {file.get('Name'): file.get('hash') for file in response.get('Entries', {})} if extra else [file.get('Name') for file in response.get('Entries', {})]

# import requests
# import os
# headers={
#            'x-api-key': os.environ.get('INSIGHT_REPORT_KEY', ''),
#            },
# with open('c:\\pin\\testfile1.txt', mode='rb') as f:
#    requests.post(url='http://127.0.0.1:5001/api/v0/add?pin=True',headers={'Content-Disposition':'form-data; name="pin"; filename="C:\\pin"','Content-Type':'application/x-directory'},
#        body={'Content-Type': 'application/json'},
#        files={})


def fixConfig(configPath=None):
    ''' we must fix the config to allow us to enable filestore in order to avoid duplication'''
    def getUserPath():
        import os
        return os.path.expanduser('~')

    def getConfigPath():
        import satorineuron.config as config
        explicit = config.var('$IPFS_PATH') + '/config'
        if explicit != '/config':
            return explicit
        return getUserPath + '/.ipfs/config'

    ''' try this CLI command first `ipfs config --json Experimental.FilestoreEnabled true`'''
    ''' already tried using the API, that can't change values, just look them up.'''
    configPath = configPath or getConfigPath()
    with open(configPath, mode='r') as f:
        x = f.read()
    x = x.replace('"FilestoreEnabled": false', '"FilestoreEnabled": true')
    with open(configPath, mode='w') as f:
        f.write(x)
