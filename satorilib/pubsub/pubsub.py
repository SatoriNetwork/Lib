# this uses the websocket-client library and represents a both the subscriber
# and the publisher connection in one. It runs the subscriber in it's own thread
# which means the only downside it has is that it cannot change the on_message
# handler, called router, until after a message has been received. This is a
# limitation, but not a serious one.

# the default router should accept the message and hold it in memory until the
# ipfs sync process is complete. Once it is complete it should send each message
# in reserve to the system that saves it to disk and routes it to the engine.
# since the engine will not even be started until after the router is complete,
# and all messages saved to the disk, this should be fine.

from typing import Union, Callable
import json
import time
import threading
from satorilib import logging


class SatoriPubSubConn(object):
    def __init__(
        self, uid: str, payload: Union[dict, str], url: Union[str, None] = None,
        router: Union['function', None] = None, listening: bool = True,
        then: Union[str, None] = None, command: str = 'key', threaded: bool = True,
        onConnect: callable = None, onDisconnect: callable = None,
        emergencyRestart: callable = None,
        *args, **kwargs
    ):
        self.c = 0
        self.uid = uid
        self.url = url or 'ws://pubsub.satorinet.io:24603'
        self.onConnect = onConnect
        self.onDisconnect = onDisconnect
        self.router = router
        self.payload = payload
        self.command = command
        self.topicTime: dict[str, float] = {}
        self.listening = listening
        self.threaded = threaded
        self.shouldReconnect = True
        self.ws = None
        self.then = then
        self.emergencyRestart = emergencyRestart
        if self.threaded:
            self.ear = threading.Thread(
                target=self.connectThenListen, daemon=True)
            self.ear.start()

    def connectThenListen(self):
        while True:
            self.connect()
            if self.ws and self.ws.connected:
                if self.then is not None:
                    time.sleep(3)
                    self.send(self.then)
                    # don't send again
                    self.then = None
                self.listen()
            time.sleep(60)

    def connect(self):
        import websocket
        if self.ws is not None:
            try:
                self.ws.close()
                self.ws = None
            except:
                pass
        self.ws = self.ws or websocket.WebSocket()
        while not self.ws.connected:
            try:
                self.ws.connect(f'{self.url}?uid={self.uid}')
                if isinstance(self.onConnect, Callable):
                    self.onConnect()
                self.send(self.command + ':' + self.payload)
                logging.info('connected to:', self.url, 'for', 'publishing' if self.router ==
                             None else 'subscriptions', 'as', self.uid, color='green')
                return self.ws
            except Exception as e:
                # except OSError as e:
                # OSError: [Errno 99] Cannot assign requested address
                # pubsub server went down
                if 'Forbidden' in str(e):
                    exit()
                logging.error(
                    e, f'\ndropped {"publishing" if self.router is None else "subscribing"} {self.url}, retrying in 60 seconds...')
                if isinstance(self.onDisconnect, Callable):
                    self.onDisconnect()
                time.sleep(60)

    def listen(self):
        while True:
            if not self.ws or not self.ws.connected:
                logging.error('WebSocket is not connected, reconnecting...')
                time.sleep(60)
                break
            try:
                response = self.ws.recv()
                try:
                    if response == '---STOP!---':
                        self.emergencyRestart()
                except Exception as _:
                    pass
                # don't break listener because of router behavior
                try:
                    if self.router is not None:
                        self.router(response)
                except Exception as _:
                    pass
            except Exception as e:
                # except WebSocketConnectionClosedException as e:
                # except ConnectionResetError:
                logging.error(
                    e, f'\nfailed while listening {self.url}, reconnecting in 60 seconds...', print=True)
                time.sleep(60)
                break

    def setTopicTime(self, topic: str):
        self.topicTime[topic] = time.time()

    # old never called, necessary?
    def reestablish(self, err: str = '', payload: str = None):
        # logging.debug('connection error', err)
        time.sleep(3)
        while True:
            try:
                logging.debug('re-establishing pubsub connection')
                self.restart(payload)
            except Exception as e:
                logging.debug(
                    'restarting pubsub connection failed', e, self.url)
                pass
            time.sleep(2)
            if (self.ws.connected):
                break

    def restart(self, payload: str = None):
        self = self.__init__(
            uid=self.uid,
            payload=self.payload,
            url=self.url,
            router=self.router,
            listening=self.listening,
            command=self.command,
            then=payload)

    def send(
        self,
        payload: Union[str, None] = None,
        title: Union[str, None] = None,
        topic: Union[str, None] = None,
        data: Union[str, None] = None,
        observationTime: Union[str, None] = None,
        observationHash: Union[str, None] = None,
    ):
        if self.ws.connected == False:
            return
        if payload is None and title is None and topic is None and data is None:
            raise ValueError(
                'payload or (title, topic, data) must not be None')
        payload = payload or (
            title + ':' + json.dumps({
                'topic': topic,
                'data': str(data),
                'time': str(observationTime),
                'hash': str(observationHash),
            }))
        try:
            self.ws.send(payload)
        except Exception as e:
            # BrokenPipeError
            # WebSocketConnectionClosedException
            # WebSocketTimeoutException
            logging.error(
                e, '\nfailed while sending to Satori Pubsub, reconnecting in 30 seconds...', print=True)
            time.sleep(30)
            self.connect()

    def publish(self, topic: str, data: str, observationTime: str, observationHash: str):
        if self.topicTime.get('topic', 0) > time.time() - 55:
            return
        self.setTopicTime(topic)
        self.send(
            title='publish',
            topic=topic,
            data=data,
            observationTime=observationTime,
            observationHash=observationHash)

    def disconnect(self, reconnect: bool = False):
        self.shouldReconnect = reconnect
        self.listening = False
        self.send(title='notice', topic='connection', data='False')
        if isinstance(self.onDisconnect, Callable):
            self.onDisconnect()
        self.ws.close()  # server should detect we closed the connection
        assert (self.ws.connected == False)
        self.ws = None

    def setRouter(self, router: 'function' = None):
        self.router = router

# install latest python3 (>3.7)
# pip3 install websocket-client
# python3 clientws.py
