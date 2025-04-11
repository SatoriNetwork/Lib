from typing import Union
import os
import json
import time
import queue
import socket
import logging
import threading
import pandas as pd
from satorilib.electrumx import ElectrumxConnection
from satorilib.electrumx import ElectrumxApi


class Subscription:
    def __init__(
        self,
        method: str,
        params: Union[list, None] = None,
        callback: Union[callable, None] = None
    ):
        self.method = method
        self.params = params or []
        self.shortLivedCallback = callback

    def __hash__(self):
        return hash((self.method, tuple(self.params)))

    def __eq__(self, other):
        if isinstance(other, Subscription):
            return self.method == other.method and self.params == other.params
        return False

    def __call__(self, *args, **kwargs):
        '''
        This is the callback that is called when a subscription is triggered.
        it takes time away from listening to the socket, so it should be short-
        lived, like saving the value to a variable and returning, or logging,
        or triggering a thread to do something such as listen to the queue and
        do some long-running process with the data from the queue.
        example:
            def foo(*args, **kwargs):
                print(f'foo. args:{args}, kwargs:{kwargs}')
        '''
        if self.shortLivedCallback is None:
            return None
        return self.shortLivedCallback(*args, **kwargs)


class Electrumx(ElectrumxConnection):
    def __init__(
        self,
        *args,
        persistent: bool = False,
        cachedPeers: str = '/Satori/Neuron/wallet/peers.csv',
        **kwargs,
    ):
        super(type(self), self).__init__(*args, **kwargs)
        self.api = ElectrumxApi(send=self.send, subscribe=self.subscribe)
        self.lock = threading.Lock()
        self.subscriptions: dict[Subscription, queue.Queue] = {}
        self.responses: dict[str, dict] = {}
        self.listenerStop = threading.Event()
        self.pingerStop = threading.Event()
        self.ensureConnectedLock = threading.Lock()
        self.startListener()
        self.lastHandshake = 0
        self.handshaked = None
        self.handshake()
        self.persistent: bool = persistent
        self.cachedPeers: str = cachedPeers
        if self.persistent:
            self.startPinger()
        self.managePeers()

    def managePeers(self):
        if self.cachedPeers != '':
            try:
                # Get peers from API
                self.peers = self.api.getPeers()
                if not self.peers:
                    logging.warning("No peers returned from API")
                    return
                
                # Process peers into a structured format
                processed_peers = []
                current_time = time.time()
                for peer in self.peers:
                    try:
                        # Validate peer structure
                        if not isinstance(peer, list) or len(peer) != 3:
                            logging.warning(f"Invalid peer structure: {peer}")
                            continue
                            
                        ip, domain, features = peer
                        if not isinstance(features, list):
                            logging.warning(f"Invalid features format for peer {ip}: {features}")
                            continue
                            
                        version = None
                        ports = []
                        port_types = []
                        
                        # Extract version and ports from features
                        for feature in features:
                            if feature.startswith('v'):
                                version = feature
                            elif feature.startswith('s') or feature.startswith('t'):
                                # Save both SSL (s) and TCP (t) ports
                                port_type = feature[0]  # 's' or 't'
                                port = feature[1:]     # The port number
                                ports.append(port)
                                port_types.append(port_type)
                        
                        # Add peer data with all available ports
                        for i, port in enumerate(ports):
                            processed_peers.append({
                                'ip': ip,
                                'domain': domain,
                                'version': version,
                                'port': port,
                                'port_type': port_types[i],  # 's' for SSL, 't' for TCP
                                'timestamp': current_time
                            })
                    except Exception as e:
                        logging.warning(f"Error processing peer {peer}: {str(e)}")
                        continue
                
                # Create DataFrame from processed peers
                new_peers_df = pd.DataFrame(processed_peers)
                
                if new_peers_df.empty:
                    logging.warning("No valid peers processed")
                    return
                
                # Handle existing cache file
                if self.cacheFileExists():
                    try:
                        # Read existing peers
                        cache_df = pd.read_csv(self.cachedPeers)
                        
                        # Add port_type column if it doesn't exist in older cache files
                        if 'port_type' not in cache_df.columns:
                            # Default to 's' for backwards compatibility
                            cache_df['port_type'] = 's'
                            
                        # Create a unique key for each peer for efficient lookup
                        new_peers_df['key'] = new_peers_df['ip'] + ':' + new_peers_df['port'].astype(str) + ':' + new_peers_df['port_type']
                        if 'key' not in cache_df.columns:
                            cache_df['key'] = cache_df['ip'] + ':' + cache_df['port'].astype(str) + ':' + cache_df['port_type']
                        
                        # Create combined dataframe with all peers
                        combined_df = pd.concat([cache_df, new_peers_df])
                        
                        # Sort by timestamp descending (newest first) and drop duplicates by key
                        # keeping only the first occurrence (which will be the newest)
                        result_df = combined_df.sort_values('timestamp', ascending=False) \
                                             .drop_duplicates(subset='key', keep='first') \
                                             .drop(columns=['key']) \
                                             .reset_index(drop=True)
                        
                        # Save updated peers
                        result_df.to_csv(self.cachedPeers, index=False)
                        logging.debug(f"Successfully updated peer cache with {len(result_df)} peers")
                    except Exception as e:
                        logging.error(f"Error updating cache file: {str(e)}")
                        # If there's an error with the cache, just write the new peers
                        if 'key' in new_peers_df.columns:
                            new_peers_df = new_peers_df.drop(columns=['key'])
                        new_peers_df.to_csv(self.cachedPeers, index=False)
                else:
                    # No cache exists, create new one
                    new_peers_df.to_csv(self.cachedPeers, index=False)
                    logging.debug(f"Created new peer cache with {len(new_peers_df)} peers")
                    
            except Exception as e:
                logging.error(f"Error in managePeers: {str(e)}")
                return

    def cacheFileExists(self):
        if self.cachedPeers != '':
            return os.path.exists(self.cachedPeers)
    
    def findSubscription(self, subscription: Subscription) -> Subscription:
        for s in self.subscriptions.keys():
            if s == subscription:
                return s
        return subscription

    def startListener(self):
        self.listenerStop.clear()
        self.listener = threading.Thread(target=self.listen, daemon=True)
        self.listener.start()

    def startPinger(self):
        self.pingerStop.clear()
        self.pinger = threading.Thread(target=self.stayConnected, daemon=True)
        self.pinger.start()

    def listen(self):

        def handleMultipleMessages(buffer: str):
            ''' split on the first newline to handle multiple messages '''
            return buffer.partition('\n')

        buffer = ''
        #while not self.listenerStop.is_set():
        while True:
            if not self.isConnected:
                time.sleep(10)
                continue
            try:
                raw = self.connection.recv(1024 * 16).decode('utf-8')
                buffer += raw
                if raw == '':
                    self.isConnected = False
                    continue
                if '\n' in raw:
                    message, _, buffer = handleMultipleMessages(buffer)
                    try:
                        r: dict = json.loads(message)
                        method = r.get('method', '')
                        if method == 'blockchain.headers.subscribe':
                            subscription = self.findSubscription(
                                subscription=Subscription(method, params=[]))
                            q = self.subscriptions.get(subscription)
                            if isinstance(q, queue.Queue):
                                q.put(r)
                            subscription(r)
                        if method == 'blockchain.scripthash.subscribe':
                            subscription = self.findSubscription(
                                subscription=Subscription(
                                    method,
                                    params=r.get(
                                        'params',
                                        ['scripthash', 'status'])[0]))
                            q = self.subscriptions.get(subscription)
                            if isinstance(q, queue.Queue):
                                q.put(r)
                            subscription(r)
                        else:
                            self.responses[
                                r.get('id', self._generateCallId())] = r
                    except json.decoder.JSONDecodeError as e:
                        logging.debug((
                            f"JSONDecodeError: {e} in message: {message} "
                            "error in _receive"))
            except socket.timeout:
                logging.debug('no activity for 10 minutes, wallet going to sleep.')
            except OSError as e:
                # Typically errno = 9 here means 'Bad file descriptor'
                logging.debug("Socket closed. Marking self.isConnected = False.")
                self.isConnected = False
            except Exception as e:
                logging.debug(f"Socket error during receive: {str(e)}")
                self.isConnected = False

    def listenForSubscriptions(self, method: str, params: list) -> dict:
        return self.subscriptions[Subscription(method, params)].get()


    def listenForResponse(self, callId: Union[str, None] = None) -> Union[dict, None]:
        then = time.time()
        while time.time() < then + 30:
            response = self.responses.get(callId)
            if response is not None:
                del self.responses[callId]
                self.cleanUpResponses()
                return response
            time.sleep(1)
        return None

    def cleanUpResponses(self):
        '''
        clear all stale responses since the key is a stringed time.time()
        '''
        currentTime = time.time()
        stale = 30
        keysToDelete = []
        for key in self.responses.keys():
            try:
                if float(key) < currentTime - stale:
                    keysToDelete.append(key)
            except Exception as e:
                logging.warning(f'error in cleanUpResponses {e}')
        for key in keysToDelete:
            del self.responses[key]

    def stayConnected(self):
        while not self.pingerStop.is_set():
            time.sleep(60*3)
            if not self.connected():
                self.connect()
                self.handshake()

    def reconnect(self) -> bool:
        self.listenerStop.set()
        #while self.listener.is_alive():
        #    time.sleep(1)
        if self.persistent:
            self.pingerStop.set()
        with self.lock:
            if super().reconnect():
                #self.startListener() # no need to restart listener, because we don't kill it when disconnetced now
                self.handshake()
                if self.persistent:
                    self.startPinger()
                self.resubscribe()
                return True
            else:
                logging.debug('reconnect failed')
                self.isConnected = False
        return False

    def connected(self) -> bool:
        if not super().connected():
            self.isConnected = False
            return False
        try:
            self.connection.settimeout(2)
            response = self.api.ping()
            #import traceback
            #traceback.print_stack()
            self.connection.settimeout(self.timeout)
            if response is None:
                self.isConnected = False
                return False
            self.isConnected = True
            return True
        except Exception as e:
            if not self.persistent:
                logging.error(f'checking connected - {e}')
            self.isConnected = False
            return False

    def ensureConnected(self) -> bool:
        with self.ensureConnectedLock:
            if not self.connected():
                logging.debug('ensureConnected() revealed wallet is not connected')
                self.reconnect()
                return self.connected()
            return True

    def handshake(self):
        try:
            self.handshaked = self.api.handshake()
            self.lastHandshake = time.time()
            return True
        except Exception as e:
            logging.error(f'error in handshake initial {e}')

    @staticmethod
    def _generateCallId() -> str:
        return str(time.time())

    def _preparePayload(self, method: str, callId: str, params: list) -> bytes:
        return (
            json.dumps({
                "jsonrpc": "2.0",
                "id": callId,
                "method": method,
                "params": params
            }) + '\n'
        ).encode()

    def send(
        self,
        method: str,
        params: list,
        callId: Union[str, None] = None,
        sendOnly: bool = False,
    ) -> Union[dict, None]:
        callId = callId or self._generateCallId()
        payload = self._preparePayload(method, callId, params)
        self.connection.send(payload)
        if sendOnly:
            return None
        return self.listenForResponse(callId)

    def subscribe(
        self,
        method: str,
        params: list,
        callback: Union[callable, None] = None,
    ):
        self.subscriptions[
            Subscription(method, params, callback=callback)
        ] = queue.Queue()
        return self.send(method, params)

    def resubscribe(self):
        if self.connected():
            for subscription in self.subscriptions.keys():
                self.subscribe(subscription.method, *subscription.params)
