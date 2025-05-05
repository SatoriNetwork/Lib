from typing import Union
import json
import uuid
import pandas as pd
import datetime as dt
from functools import partial

# from satorilib.utils.hash import generatePathId
# from enum import Enum


class StreamId:
    """unique identifier for a stream"""

    @staticmethod
    def generateUUID(data: Union['StreamId', str, dict] = None) -> uuid:
        namespace = uuid.NAMESPACE_DNS
        if isinstance(data, StreamId):
            #data = data.jsonId
            data = data.topic(asJson=False)
        if isinstance(data, dict):
            #data = StreamId.fromMap(data).jsonId
            values = [
                data.get('source'),
                data.get('author'),
                data.get('stream'),
                data.get('target')]
            data = ':'.join(str(v) for v in values)
        return uuid.uuid5(namespace, data)

    @staticmethod
    def keys():
        return ['source', 'author', 'stream', 'target']

    def __init__(
        self,
        source: str,
        author: str,
        stream: str,
        target: str = '',
    ):
        self.__source = source
        self.__author = author
        self.__stream = stream
        self.__target = target
        # disallowing target to be None (for hashability) means an empty string
        # is not a valid target, which it might be in the real world. so we
        # allow target to be None, indicating that a stream observation is a
        # value in and of itself, rather than structure of values (such as a
        # dictionary or a json object in which case the target would be a string
        # corresponding to the key, or list in which case target might be the
        # index).

    @property
    def source(self):
        return self.__source

    @property
    def author(self):
        return self.__author

    @property
    def stream(self):
        return self.__stream

    @property
    def target(self):
        return self.__target

    @property
    def mapId(self) -> dict[str, str]:
        return {
            'source': self.__source,
            'author': self.__author,
            'stream': self.__stream,
            'target': self.__target}

    @property
    def jsonId(self) -> str:
        return json.dumps(self.mapId)

    @property
    def uuid(self) -> str:
        return str(StreamId.generateUUID(self))

    @property
    def id(self)-> tuple[str, str, str, Union[str, None]]:
        return (self.__source, self.__author, self.__stream, self.__target)

    @property
    def strId(self) -> str:
        return str((self.__source, self.__author, self.__stream, self.__target)).replace("'", '')

    # TODO: remove after datamanager is live, this is used to determine the
    #       location of the dataset on disk as a csv, if we ever do save to
    #       disk we should use something else anyway
    @property
    def idString(self):  # todo: make this .id and the .key a tuple
        return (
            (self.__source or "")
            + (self.__author or "")
            + (self.__stream or "")
            + (self.__target or "")
        )

    def topic(
        self,
        asJson: bool = True,
        authorAsPubkey=False
    ) -> Union[str, dict[str, str]]:
        """
        the topic (id) for this stream.
        this is how the pubsub system identifies the stream.
        """
        if asJson:
            return self.topicJson(authorAsPubkey=authorAsPubkey)
        return {
            "source": self.__source,
            "pubkey" if authorAsPubkey else "author": self.__author,
            "stream": self.__stream,
            "target": self.__target,
        }

    def topicJson(self, authorAsPubkey=False) -> str:
        """
        the topic (id) for this stream.
        this is how the pubsub system identifies the stream.
        """
        return json.dumps(self.topic(asJson=False, authorAsPubkey=authorAsPubkey))

    def __repr__(self):
        return str(self.mapId)

    def __str__(self):
        return str(self.__repr__())

    def __eq__(self, other):
        if isinstance(other, StreamId):
            return (
                self.source == other.source and
                self.author == other.author and
                self.stream == other.stream and
                self.target == other.target)
        return False

    def __hash__(self):
        """
        note: target can be None meaning, the stream is not a dictionary of
        values. yet we still have to hash the object, thus the use of np.inf
        which only has the side effect of barring np.inf as a valid target when
        a stream by the same id and no target also exists. (essentially safe).
        this is a better choice than 0 or -1 since a stream observation could be
        a list of values and the target an index for that list.

        note 0: the above note is helpful, but np.inf cannot be concatenated
        with strings so it would be preferable to use a random string here,
        rather than an empty string becuase it would be less likely to clash.
        we'll use the Mersenne Twister algorithm with seed 'dR3jS9lMqXcTfYvA':
        q7jDmL8kV4HvCnX

        note 1: that's a great idea, but here's the situation: the server has
        this same problem and solves it with an empty string. So since this
        problem manifest at the domain level, not merely in this equality check,
        we'll use that solution for now.

        note 2: alright, so that doesn't work in this endpoint:
        /remove_stream/<source>/<stream>/<target> because target is an empty
        string. so. target always has to be a non-null non-empty string. I think
        the default should be a - then. To be honest... the best solution is to
        get rid of target altogether. the domain seems broken here because why
        have hierarchy at all if it's limited to just 3 levels. You have to deal
        with all that complexity, but you don't get the versatility of a real
        hierarchy. so we can either fix the domain to remove target altogether,
        or we can use a '-' as the default. 3 levels would be fine if it was EAV
        but it's not. the better domain design would be unique streamid (a hash)
        with a lookup table to what that stream corresponds to, and allow that
        to be an unlimited hierarchy requiring at least source. for now we'll
        use the '-' solution which requires a server change anyway.

        note 3: instead of that I decided to change the endpoint to
        /remove_stream/<topic> and parse out the topic instead. it's just less
        work for the same quality work around.
        """
        return hash(
            self.__source + self.__author +
            self.__stream + (self.__target or ""))

    @property
    def generateHash(self) -> str:
        from satorilib.utils.hash import generatePathId, hashIt
        return generatePathId(streamId=self)

    @property
    def key(self):
        return self.id

    def new(
        self,
        source: str = None,
        author: str = None,
        stream: str = None,
        target: str = None,
    ):
        return StreamId(
            source=source or self.source,
            author=author or self.author,
            stream=stream or self.stream,
            target=target or self.target)

    @staticmethod
    def fromMap(map: dict = None):
        return StreamId(
            source=(map or {}).get("source"),
            author=(map or {}).get("author", (map or {}).get("pubkey")),
            stream=(map or {}).get("stream", (map or {}).get("name")),
            target=(map or {}).get("target"))

    @staticmethod
    def fromTopic(topic: str = None):
        return StreamId.fromMap(json.loads(topic or "{}"))


class StreamUuid(StreamId):
    '''unique identifier for a stream'''

    def __init__(self, uuid: str):
        super().__init__(source='', author='', stream='', target='')
        self.uuid = uuid


# now that we've made the StreamId hashable this is basically unnecessary.
class StreamIdMap:
    def __init__(self, streamId: StreamId = None, value=None):
        if streamId is None:
            self.d = dict()
        else:
            self.d = {streamId: value}

    def __repr__(self):
        return str(self.d)

    def __str__(self):
        return str(self.__repr__())

    def add(self, streamId: StreamId, value=None):
        self.d[streamId] = value

    def addAll(self, streamIds: list[StreamId], values: list[StreamId]):
        for streamId, value in zip(streamIds, values):
            self.add(streamId, value)

    def keys(self):
        return self.d.keys()

    def streams(self):
        return {k.new(clearTarget=True) for k in self.keys()}

    @staticmethod
    def _condition(key: StreamId, streamId: StreamId, default: bool = True):
        return all(
            [
                x == k or (x is None and default)
                for x, k in zip(
                    [
                        streamId.source,
                        streamId.author,
                        streamId.stream,
                        streamId.target,
                    ],
                    [key.source, key.author, key.stream, key.target],
                )
            ]
        )

    def remove(self, streamId: StreamId, greedy: bool = True):
        condition = partial(StreamIdMap._condition,
                            streamId=streamId, default=greedy)
        removed = []
        for k in self.d.keys():
            if condition(k):
                removed.append(k)
        for k in removed:
            del self.d[k]
        return removed

    def get(self, streamId: StreamId = None, default=None, greedy: bool = False):
        if streamId is None:
            return self.d
        condition = partial(StreamIdMap._condition,
                            streamId=streamId, default=greedy)
        matches = [self.d.get(k) for k in self.d.keys() if condition(k)]
        return matches[0] if len(matches) > 0 else default

    def getAll(self, streamId: StreamId = None, greedy: bool = True):
        if streamId is None:
            return self.d
        condition = partial(StreamIdMap._condition,
                            streamId=streamId, default=greedy)
        return {k: v for k, v in self.d.items() if condition(k)}

    def isFilled(self, streamId: StreamId, greedy: bool = True):
        condition = partial(StreamIdMap._condition,
                            streamId=streamId, default=greedy)
        matches = [self.d.get(
            k) is not None for k in self.d.keys() if condition(k)]
        return len(matches) > 0 and all(matches)

    def getAllAsList(self, streamId: StreamId = None, greedy: bool = True):
        matches = self.getAll(streamId, greedy=greedy)
        return [(k, v) for k, v in matches.items()]


class Stream:

    minimumCadence = 60 * 10 * 6

    def __init__(
        self,
        streamId: StreamId,
        cadence: int = None,
        offset: int = None,  # unused... for now
        datatype: str = None,  # unused... for now
        description: str = None,  # unused... for now
        tags: str = None,  # unused... for now
        url: str = None,  # unused... for now
        uri: str = None,
        headers: str = None,
        payload: str = None,
        hook: str = None,
        history: str = None,
        ts: str = None,
        predicting: StreamId = None,
        pinned: int = None,
        reason: StreamId = None,
        reason_is_primary: bool = None,
        **kwargs,
    ):
        self.streamId = streamId
        self.cadence = cadence
        self.offset = offset or kwargs.get('utc_offset')
        self.datatype = datatype
        self.description = description
        self.tags = tags
        self.url = url
        self.uri = uri
        self.headers = headers
        self.payload = payload
        self.hook = hook
        self.history = history
        self.ts = ts
        self.predicting = predicting
        self.pinned = pinned
        self.reason = reason
        self.reason_is_primary = reason_is_primary
        self.kwargs = kwargs

    def __str__(self):
        return str(vars(self))

    def __repr__(self):
        return self.__str__()

    @property
    def id(self):
        return self.streamId

    @staticmethod
    def fromMap(rep: dict = None):
        def extractKnownKwarg(key: str, rep: dict = None):
            rep = rep or {}
            kwargs = rep.get("kwargs", {})
            if key in kwargs.keys() and key not in rep.keys():
                rep[key] = kwargs.get(key)
                rep["kwargs"] = {k: v for k, v in kwargs.items() if k != key}
            return rep

        def extractPredicting(key: str, rep: dict = None):
            predictionKeys = [
                f"{key}_source",
                f"{key}_author",
                f"{key}_stream",
                f"{key}_target",
            ]
            rep = rep or {}
            if all([x in rep.keys() for x in predictionKeys]):
                rep[key] = StreamId.fromMap(
                    {
                        k.replace(f"{key}_", ""): v
                        for k, v in rep.items()
                        if k in predictionKeys
                    }
                )
                rep = {k: v for k, v in rep.items() if k not in predictionKeys}
            return rep

        rep = extractKnownKwarg("ts", rep)
        rep = extractKnownKwarg("reason_is_primary", rep)
        rep = extractPredicting("predicting", rep)  # publish prediction of x
        rep = extractPredicting("reason", rep)  # subscribing to predict x
        return Stream(
            streamId=StreamId.fromMap(rep),
            **{k: rep[k] for k in rep.keys() if k not in StreamId.keys()},
        )

    def asMap(self, noneToBlank=False, includeTopic=True):
        return {
            **(
                {k: v if v is not None else "" for k, v in vars(self).items()}
                if noneToBlank
                else vars(self)
            ),
            **({"topic": self.streamId.jsonId} if includeTopic else {}),
        }


class StreamOverview:

    def __init__(
        self,
        streamId: StreamId,
        value,
        values=None,
        errs=None,
        pinned=False,
        predictions=None,
        # dataset=None,
        subscribers: int = "-",
        accuracy: float = "-",
        prediction: float = "-",
    ):
        self.streamId = streamId
        self.subscribers = subscribers
        self.accuracy = accuracy
        self.prediction = prediction
        self.value = value
        self.pinned = pinned
        self.values = values or []
        self.errs = errs or []
        self.predictions = predictions or []
        # self.dataset = dataset

    def load(self, streamOverview: "StreamOverview"):
        self.streamId = streamOverview.streamId
        self.subscribers = streamOverview.subscribers
        self.accuracy = streamOverview.accuracy
        self.prediction = streamOverview.prediction
        self.value = streamOverview.value
        self.pinned = streamOverview.pinned
        self.values = streamOverview.values
        self.errs = streamOverview.errs
        self.predictions = streamOverview.predictions
        # self.dataset = streamOverview.dataset

    def __str__(self):
        # return str(vars(self))
        return str(
            {
                **{
                    k: v
                    for k, v in vars(self).items()
                    if k != "streamId" and k != "pinned"
                },
                **{
                    "pinned": 1 if self.pinned else 0,
                    "hashed": self.hashed,
                    "source": self.streamId.source,
                    "author": self.streamId.author,
                    "stream": self.streamId.stream,
                    "target": self.streamId.target,
                },
            }
        )

    def __repr__(self):
        return self.__str__()

    @property
    def author(self):
        return self.streamId.author

    @property
    def source(self):
        return self.streamId.source

    @property
    def stream(self):
        return self.streamId.stream

    @property
    def target(self):
        return self.streamId.target

    @property
    def topic(self):
        return self.streamId.jsonId

    @property
    def hashed(self):
        return self.streamId.generateHash


class StreamOverviews:

    def __init__(self, engine):
        self.engine = engine
        self.overview = StreamOverviews.blank()
        self.viewed = False
        self.setIt()

    def setIt(self):
        self.overview = [model.overview() for model in self.engine.models]
        self.viewed = False

    def setViewed(self):
        self.viewed = True

    @staticmethod
    def demo():
        return [
            StreamOverview(
                streamId=StreamId(
                    source="Streamr",
                    author="DATAUSD",
                    stream="DATAUSD/binance/ticker",
                    target="Close",
                ),
                subscribers=3,
                accuracy=97.062,
                prediction="3621.00",
                value="3548.00",
                pinned=True,
                errs=[],
                # dataset=None,
                values=[1, 2, 3],
                predictions=[1, 2, 3],
            )
        ]

    @staticmethod
    def blank():
        return [
            StreamOverview(
                streamId=StreamId(source="-", author="-",
                                  stream="-", target="-"),
                subscribers="-",
                accuracy="-",
                prediction="-",
                value="-",
                pinned=False,
                errs=[],
                # dataset=None,
                values=[1, 1, 1],
                predictions=[1, 1, 1],
            )
        ]


class Observation:

    def __init__(self, raw, **kwargs):
        self.raw = raw
        self.value: Union[str, None] = None
        self.data: Union[dict, None] = None
        self.hash: Union[dict, None] = None
        self.time: Union[str, None] = None
        self.streamId: Union[StreamId, None] = None
        self.observationHash: Union[int, None] = None
        self.df: pd.Union[pd.DataFrame, None] = None
        self.observationTime: Union[str, None] = None
        self.target: Union[str, None] = None
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return str(vars(self))

    def __repr__(self):
        return f"Observation of {self.streamId}: " + str(
            {
                "time": self.time,
                "data": self.value,
                "hash": self.observationHash,
            }
        )

    @staticmethod
    def parse(raw):
        if (
            isinstance(raw, dict)
            and "topic" in raw.keys()
            and "data" in raw.keys()
            and "hash" in raw.keys()
            and "time" in raw.keys()
        ) or (
            isinstance(raw, str)
            and '"topic":' in raw
            and '"data":' in raw
            and '"hash":' in raw
            and '"time":' in raw
        ):
            return Observation.fromTopic(raw)
        return Observation.fromGuess(raw)

    @staticmethod
    def fromTopic(raw, realtime: bool = True):
        '''
        this is the structur that hte Satori PubSub delivers data in: {
            'topic': '{"source": "satori", "author": "02a85fb71485c6d7c62a3784c5549bd3849d0afa3ee44ce3f9ea5541e4c56402d8", "stream": "WeatherBerlin", "target": "temperature"}',
            'time': '2024-04-13 17:53:00.661619',
            'data': 4.2,
            'hash': 'abc'}
        if realtime is false then we trust the observationTime because we're
        running this function on past data. however, we probably never do that.
        '''
        if isinstance(raw, str):
            j = json.loads(raw)
        elif isinstance(raw, dict):
            j = raw
        topic = j.get("topic", None)
        streamId = StreamId.fromTopic(topic)
        now = dt.datetime.now(dt.timezone.utc)
        nowStr = now.strftime('%Y-%m-%d %H:%M:%S.%f')
        if not realtime:
            observationTime = j.get('time', )
            try:
                observationDt = dt.datetime.strptime(
                    observationTime,
                    format='%Y-%m-%d %H:%M:%S.%f')
                if (observationDt > now or observationDt < now - 60):
                    observationDt = now
                    observationTime = nowStr
            except Exception as _:
                observationDt = now
                observationTime = nowStr
        else:
            observationTime = j.get('time', now)
        observationHash = j.get('observationHash', j.get('hash', None))
        value = j.get('data', None)
        target = None
        df = pd.DataFrame(
            {
                (streamId.source, streamId.author, streamId.stream, streamId.target): [
                    value
                ]
            },
            index=[observationTime],
        )
        # I don't understand whey we still have a StreamObservationId
        # or the multicolumn identifier... maybe it's for the engine?
        # I think we should just save it to disk like this:
        # observationHash = j.get('hash', None)
        # df = pd.DataFrame(
        #    {'value': [value],  'hash': [observationHash]},
        #    index=[observationTime])
        return Observation(
            raw=raw,
            topic=topic,
            streamId=streamId,
            observationTime=observationTime,
            observationHash=observationHash,
            value=value,
            target=target,
            df=df,
        )

    @staticmethod
    def fromGuess(raw):
        """{
            'source:"streamrSpoof",'
            'author:"pubkey",'
            'stream:"simpleEURCleaned",'
            'observation': 3675,
            'time': "2022-02-16 02:52:45.794120",
            'content': {
                'High': 0.81856,
                'Low': 0.81337,
                'Close': 0.81512}}
        note: if observed-time is missing, define it here.
        """
        if isinstance(raw, str):
            j = json.loads(raw)
        elif isinstance(raw, dict):
            j = raw
        elif isinstance(raw, tuple):
            j = {}
            for k, v in raw:
                j[k] = v
        else:
            j = raw
        observationTime = j.get(
            "time", dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
        )
        observationHash = j.get("observationHash", j.get("hash", None))
        content = j.get("content", {})
        streamId = StreamId(
            source=j.get("source", None),
            author=j.get("author", None),
            stream=j.get("stream", None),
            target=j.get("target", None),
        )
        value = None
        if isinstance(content, dict):
            if len(content.keys()) == 1:
                streamId.new(target=content.keys()[0])
                value = content.get(streamId.target)
            df = pd.DataFrame(
                {
                    (streamId.source, streamId.author, streamId.stream, target): values
                    for target, values in list(content.items()) + ([])
                },
                index=[observationTime],
            )
        # todo: handle list
        # elif isinstance(content, list): ...
        else:
            value = content
            df = pd.DataFrame(
                {
                    (streamId.source, streamId.author, streamId.stream, None): [content]
                    + (
                        [("StreamObservationId", observationHash)]
                        if observationHash is not None
                        else []
                    )
                },
                index=[observationTime],
            )
        return Observation(
            raw=raw,
            content=content,
            observationTime=observationTime,
            observationHash=observationHash,
            streamId=streamId,
            value=value,
            df=df,
        )

    @property
    def key(self):
        return self.streamId

    @property
    def timestamp(self):
        return self.observationTime


class StreamPair:
    """Matches the Subscription streams with the Publication Streams"""

    def __init__(self, subscription: Stream, publication: Stream):
        self.subscription = subscription
        self.publication = publication


class StreamPairs:
    """Matches the Subscription streams with the Publication Streams"""

    def __init__(self, subscriptions, publications):
        self.subscriptions = subscriptions
        self.publications = publications
        self.filtered_subscriptions = None

    def get_publication_streams(self):
        return {pub.streamId.stream.replace("_p", ""): pub for pub in self.publications}

    def filter_subscriptions(self):
        pub_streams = self.get_publication_streams()

        self.filtered_subscriptions = [
            sub
            for sub in self.subscriptions
            if sub.streamId.stream in pub_streams
            or sub.streamId.stream.replace("_p", "") in pub_streams
        ]
        return self.filtered_subscriptions

    def get_matched_pairs(self) -> tuple[list[Stream], list[Stream]]:
        pub_streams = self.get_publication_streams()
        sub_list = []
        pub_list = []

        for sub in self.subscriptions:
            stream_name = sub.streamId.stream
            base_name = stream_name.replace("_p", "")

            if stream_name in pub_streams or base_name in pub_streams:
                matching_pub = next(
                    (
                        pub
                        for pub in self.publications
                        if pub.streamId.stream.replace("_p", "") == base_name
                    ),
                    None,
                )
                if matching_pub:
                    sub_list.append(sub)
                    pub_list.append(matching_pub)

        return sub_list, pub_list

    def get_matched_objects(self) -> list[StreamPair]:
        return [StreamPair(s, p) for s, p in zip(self.subscriptions, self.publications)]
