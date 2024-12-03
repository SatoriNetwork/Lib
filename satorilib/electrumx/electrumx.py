from typing import Union
import logging
import socket
import json
import time
import queue
import threading
from satorilib.electrumx import ElectrumxConnection
from satorilib.electrumx import ElectrumxApi

class Subscription:
    def __init__(
        self,
        method: str,
        params: list,
        callback: Union[callable, None] = None
    ):
        self.method = method
        self.params = params
        self.shortLivedCallback = callback

    def __hash__(self):
        return hash((self.method, self.params))

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
        **kwargs,
    ):
        super(type(self), self).__init__(*args, **kwargs)
        self.api = ElectrumxApi(send=self.send, subscribe=self.subscribe)
        self.lock = threading.Lock()
        self.subscriptions: dict[Subscription, queue.Queue] = {}
        self.responses: dict[str, dict] = {}
        self.quiet = queue.Queue()
        self.listenerStop = threading.Event()
        self.pingerStop = threading.Event()
        self.startListener()
        self.lastHandshake = 0
        self.handshaked = None
        self.handshake()
        self.persistent = persistent
        if self.persistent:
            self.startPinger()

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
        while not self.listenerStop.is_set():
            if not self.isConnected:
                time.sleep(1)
                continue
            try:
                raw = self.connection.recv(1024 * 16).decode('utf-8')
                buffer += raw
                if raw == '':
                    self.quiet.put(time.time())
                    self.isConnected = False
                    continue
                if '\n' in raw:
                    message, _, buffer = handleMultipleMessages(buffer)
                    try:
                        r: dict = json.loads(message)
                        method = r.get('method', '')
                        if method == 'blockchain.headers.subscribe':
                            subscription = self.findSubscription(
                                subscription=Subscription(method))
                            self.subscriptions[subscription].put(r)
                            subscription(r)
                        if method == 'blockchain.scripthash.subscribe':
                            subscription = self.findSubscription(
                                subscription=Subscription(
                                    method,
                                    params=r.get(
                                        'params',
                                        ['scripthash', 'status'])[0]))
                            self.subscriptions[subscription].put(r)
                            subscription(r)
                        else:
                            self.responses[r.get('id', self._generateCallId())] = r
                    except json.decoder.JSONDecodeError as e:
                        logging.error((
                            f"JSONDecodeError: {e} in message: {message} "
                            "error in _receive"))
                        self.quiet.put(time.time())
            except socket.timeout:
                logging.warning("Socket timeout occurred during receive.")
                self.quiet.put(time.time())
            #except Exception as e:
            #    logging.error(f"Socket error during receive: {str(e)}")
            #    self.quiet.put(time.time())
            #    self.isConnected = False

    def listenForSubscriptions(self, method: str):
        return self.subscriptions[method].get()

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

    def reconnect(self):
        self.listenerStop.set()
        if self.persistent:
            self.pingerStop.set()
        with self.lock:
            super().reconnect()
            self.startListener()
            self.handshake()
            if self.persistent:
                self.startPinger()
            self.resubscribe()

    def connected(self) -> bool:
        if not super().connected():
            self.isConnected = False
            return False
        try:
            response = self.api.ping()
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
        if not self.connected():
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
        x = self.listenForResponse(callId)
        return x

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
