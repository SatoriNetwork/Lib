from typing import Union
import logging
import socket
import json
import time
import queue
import threading
from satorilib.electrumx import ElectrumxConnection
from satorilib.electrumx import ElectrumxApi


class Electrumx(ElectrumxConnection):
    def __init__(
        self,
        *args,
        address: str = '',
        scripthash: str = '',
        persistent: bool = False,
        **kwargs,
    ):
        super(type(self), self).__init__(*args, **kwargs)
        self.api = ElectrumxApi(
            address=address,
            scripthash=scripthash,
            send=self.send,
            subscribe=self.subscribe)
        self.lock = threading.Lock()
        self.subscriptions: dict[str, queue.Queue] = {}
        self.subscriptionParams: dict[str, tuple] = {}
        self.responses = queue.Queue()
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
                        r = json.loads(message)
                        method = r.get('method', '')
                        if 'subscribe' in method:
                            print(f'adding to subscriptions for {method} {r}')
                            self.subscriptions[method].put(r)
                        else:
                            print(f'adding to responses {r}')
                            self.responses.put(r)
                    except json.decoder.JSONDecodeError as e:
                        logging.error((
                            f"JSONDecodeError: {e} in message: {message} "
                            "error in _receive"))
                        self.quiet.put(time.time())
            except socket.timeout:
                logging.warning("Socket timeout occurred during receive.")
                self.quiet.put(time.time())
            except Exception as e:
                logging.error(f"Socket error during receive: {str(e)}")
                self.quiet.put(time.time())
                self.isConnected = False

    def listenForSubscriptions(self, method: str):
        return self.subscriptions[method].get()

    def listenForResponse(self):
        return self.responses.get(timeout=30)

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
            response = self.send('server.ping')
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

    def handshake(self):
        try:
            method = 'server.version'
            name = f'Satori Neuron {time.time()}'
            assetApiVersion = '1.10'
            self.handshaked = self.send(method, name, assetApiVersion)
            self.lastHandshake = time.time()
            return True
        except Exception as e:
            logging.error(f'error in handshake initial {e}')

    def _preparePayload(self, method: str, *args):
        return (
            json.dumps({
                "jsonrpc": "2.0",
                "id": int(time.time()*10000000),
                "method": method,
                "params": args
            }) + '\n'
        ).encode()

    def send(
        self,
        method: str,
        *args,
        sendOnly: bool = False,
    ) -> Union[dict, list, None]:
        payload = self._preparePayload(method, *args)
        with self.lock:
            print('sending...')
            self.connection.send(payload)
            if sendOnly:
                return None
            print('waiting for response...')
            return self.listenForResponse()

    def subscribe(self, method: str, *args):
        self.subscriptions[method] = queue.Queue()
        self.subscriptionParams[method] = args
        return self.send(method, *args)

    def resubscribe(self):
        if self.connected():
            for method in self.subscriptions.keys():
                self.subscribe(
                    method, *self.subscriptionParams.get(method, []))
