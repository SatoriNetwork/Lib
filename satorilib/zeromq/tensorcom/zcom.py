import collections
import time
from builtins import object
from urllib.parse import urlparse
import braceexpand
import numpy as np
# import torch
# from torch.utils.data import IterableDataset

import zmq
import logging
logging.getLogger().setLevel(logging.INFO)

from . import tenbin


default_context = zmq.Context()


schemes = dict(
    # (KIND, BIND)
    zclient=(zmq.REQ, False),
    zserver=(zmq.REP, True),
    zpush=(zmq.PUSH, False),
    zpull=(zmq.PULL, True),
    zpub=(zmq.PUB, True),
    zsub=(zmq.SUB, False),
    zrpush=(zmq.PUSH, True),
    zrpull=(zmq.PULL, False),
    zrpub=(zmq.PUB, False),
    zrsub=(zmq.SUB, True),
)


class Statistics(object):
    """Compute running statistics over numbers, including rates. """

    def __init__(self, horizon=1000):
        """

        :param horizon:  (Default value = 1000)

        """
        self.horizon = horizon
        self.reset()

    def reset(self):
        """Reset the statistics"""
        self.start = time.time()
        self.last = time.time()
        self.count = 0
        self.total = 0
        self.recent = collections.deque(maxlen=self.horizon)

    def add(self, x):
        """Add a value to the statistics.

        :param x: value to add

        """
        self.last = time.time()
        self.count += 1
        self.total += x
        self.recent.append((self.last, x))

    def rate(self):
        """Compute the rate."""
        if self.count == 0:
            return 0
        return self.count / (self.last - self.start)

    def throughput(self):
        """Compute the throughput."""
        if self.count == 0:
            return 0
        return self.total / (self.last - self.start)

    def recent_rate(self):
        """Compute the recent rate."""
        if self.count == 0:
            return 0
        delta = self.recent[-1][0] - self.recent[0][0]
        if delta == 0:
            return 0
        return len(self.recent) / delta

    def recent_throughput(self):
        """Compute the recent throughput."""
        if self.count == 0:
            return 0
        total = sum(r[1] for r in self.recent)
        delta = self.recent[-1][0] - self.recent[0][0]
        if delta == 0:
            return 0
        return total / delta

    def summary(self):
        """Return a summary of recent statistics."""
        return "rate {:1f} msg/s throughput {:.2e} bytes/s".format(
            self.recent_rate(), self.recent_throughput()
        )


# def tonumpy(dtype=None, transpose=True):
#     """Curried any-to-numpy converter.

#     :param dtype: desired dtype (Default value = None)
#     :param transpose: whether to transpose images from PyTorch (Default value = True)

#     """

#     def f(a):
#         """

#         :param a:

#         """
#         import torch

#         if isinstance(a, torch.Tensor):
#             if a.ndim == 3 and a.shape[0] in [3, 4]:
#                 a = a.permute(1, 2, 0)
#             elif a.ndim == 4 and a.shape[1] in [3, 4]:
#                 a = a.transpose(0, 2, 3, 1)
#             return a.detach().cpu().numpy()
#         else:
#             return a

#     return f


# def totorch(dtype=None, device="cpu", transpose=True):
#     """Curried any-to-torch converter.

#     :param dtype: desired dtype (Default value = None)
#     :param device: desired device placement (Default value = "cpu")
#     :param transpose: transpose images to PyTorch conventions (Default value = True)

#     """

#     def f(a):
#         """

#         :param a:

#         """

#         if isinstance(a, np.ndarray):
#             dtype_ = dtype
#             if dtype_ is None:
#                 if a.dtype in [np.float16, np.float32, np.float64]:
#                     dtype_ = torch.float32
#                 elif a.dtype in [np.int16, np.uint16, np.int32, np.int64]:
#                     dtype_ = torch.int64
#             elif isinstance(dtype_, str):
#                 dtype_ = getattr(torch, dtype_)
#             if a.ndim == 3 and a.shape[2] in [3, 4]:
#                 a = a.transpose(2, 0, 1)
#             elif a.ndim == 4 and a.shape[3] in [3, 4]:
#                 a = a.transpose(0, 3, 1, 2)
#             return torch.as_tensor(a, device=device, dtype=dtype_)
#         else:
#             return a

#     return f


def transform_with(sample, transformers):
    """Given a list of values and functions, apply functions to values.

    This does nothing if the list of functions is None or empty.
    If there are fewer transformers than the length of the list, it wraps around.

    :param sample: list of values
    :param transformers: list of functions to apply to values

    """
    if transformers is None or len(transformers) == 0:
        return sample
    result = list(sample)
    ntransformers = len(transformers)
    assert len(sample) >= ntransformers
    for i in range(len(sample)):
        f = transformers[i % ntransformers]
        if f is not None:
            result[i] = f(sample[i])
    return result


def listify(x):
    """Turn argument into a list.

    This is a convenience function that allows strings
    to be used as a shorthand for [string] in some arguments.

    Returns None for None.
    Returns a list for a list or tuple.
    Returns [x] for anything else.

    :param x: value to be listified.

    """
    if x is None:
        return None
    elif isinstance(x, (list, tuple)):
        return x
    else:
        return [x]


# converter_table = dict(torch=totorch(), torch_cuda=totorch(device="cuda"), numpy=tonumpy())


def estimate_bytes(a):
    if isinstance(a, (bytearray, str)):
        return len(a)
    elif isinstance(a, np.ndarray):
        return a.nbytes
    else:
        return 8


def zconnect(url, context=default_context):
    """Explicitly connect to a ZMQ socket.

    :param url: ZMQ-URL to connect to  (Default value = "")
    :param topic: topic to subscribe to for SUB sockets (Default value = "")

    """
    addr = urlparse(url)
    scheme, transport = (addr.scheme.split("+", 2) + ["tcp"])[:2]
    kind, bind = schemes[scheme]
    logging.info("kind %s bind %s", kind, bind)
    socket = context.socket(kind)
    location = transport + "://" + addr.netloc
    if transport == "ipc":
        location += addr.path
    socket.setsockopt(zmq.LINGER, 0)
    if bind:
        logging.info("binding to %s", location)
        socket.bind(location)
    else:
        logging.info("connecting to %s", location)
        socket.connect(location)
    if kind == zmq.SUB:
        topic = "" if addr.fragment is None else addr.fragment
        logging.info("subscribing to '%s'", topic)
        socket.setsockopt_string(zmq.SUBSCRIBE, topic)
    return socket


class Connection(object):
    """A class for sending/receiving tensors via ZMQ sockets."""

    def __init__(
        self,
        url=None,
        epoch=100000,
        total=-1,
        multipart=True,
        infos=None,
        device=None,
        allow64=False,
        raw=False,
        batch_transforms=None,
        batch_count=True,
        converters=None,
        report=-1,
        stats_horizon=1000,
        noexpand=False,
    ):
        """Initialize a connection.

        :param url:  ZMQ-URL to connect to (Default value = None)
        :param epoch: length of an epoch, for len() (Default value = 100000)
        :param total: total number of samples (Default value = -1)
        :param multipart: send tensors in multipart messages (Default value = True)
        :param infos: info fields for tensors (Default value = [""])
        :param device: device placement for tensors (None=numpy, else torch) (Default value = None)
        :param allow64: allow 64bit values on sending (Default value = False)
        :param raw: return undecoded tensor data (Default value = False)
        :param batch_transforms: list of functions to apply to each sample (Default value = None)
        :param converters: list of functions to apply after batch_transforms (Default value = None)
        :param report: how frequently to report stats when iterating (Default value = -1)
        :param stats_horizon: horizon for computing stats (Default value = 1000)
        :param noexpand: do not expand braces in URLs (Default value = False)

        """
        self.stats = Statistics(stats_horizon)
        self.multipart = multipart
        self.infos = infos
        self.device = device
        self.allow64 = allow64
        self.context = default_context
        self.socket = None
        self.raw = False
        self.epoch = epoch
        self.total = total
        self.batch_transforms = listify(batch_transforms)
        self.batch_count = batch_count
        # if isinstance(converters, str):
        #     converters = converter_table.get(converters, [])
        self.converters = listify(converters)
        self.count = 0
        self.report = -1
        self.sampler = None  # compatibility with DataLoader
        self.batch_sampler = None  # compatibility with DataLoader
        self.batch_size = 1
        if url is not None:
            if isinstance(url, str):
                url = [url]
            if not noexpand:
                urls = []
                for u in url:
                    urls += list(braceexpand.braceexpand(u))
            else:
                urls = url
            self.connect(urls)

    def connect(self, url):

        if isinstance(url, (list, tuple)):
            for u in url:
                self.connect(u)
            return
        try:
            self.socket = zconnect(url)
        except Exception as e:
            print(f"error: url {url}")
            raise e

    def close(self):
        """Close the connection."""
        self.socket.close()
        self.socket = None
        self.context = None

    def send(self, data, *, allow64=False):
        """Send data over the connection.

        :param data: list of tensors  (Default value = False)
        :param allow64: allow 64 bit data (Default value = False)

        """
        tenbin.check_acceptable_input_type(data, allow64)
        if self.multipart:
            tenbin.zsend_multipart(self.socket, data, self.infos)
        else:
            tenbin.zsend_single(self.socket, data, self.infos)
        self.stats.add(sum(a.nbytes for a in data))

    def recv(self, flags=0):
        """Receive data from the connection."""
        if self.raw:
            self.socket.recv_multipart()
        if self.multipart:
            data = tenbin.zrecv_multipart(self.socket, self.infos, flags=flags)
        else:
            data = tenbin.zrecv_single(self.socket, self.infos, flags=flags)
        tenbin.check_acceptable_input_type(data, True)
        if isinstance(data, tuple):
            data = list(data)
        self.stats.add(sum(estimate_bytes(a) for a in data))
        data = transform_with(data, self.batch_transforms)
        data = transform_with(data, self.converters)
        self.batch_size = len(data[0])
        return data

    def batchsize(self, xs):
        if self.batch_count:
            return len(xs[0])
        else:
            return 1

    def serve(self, source, *, report=-1):
        """Serve data from an iterator.

        :param source: iterator yielding lists/tuples of tensors
        :param report: how often to report statistics (Default value = -1)

        """
        count = 0
        next_report = 0
        for sample in source:
            self.send(sample)
            if report > 0 and count >= next_report:
                print("count", count, self.stats.summary())
                next_report += report
            count += self.batchsize(sample)

    def items(self, report=-1):
        """Receive data through an iterator"""
        count = 0
        next_report = 0
        while True:
            if self.total > 0 and self.count >= self.total:
                return
            result = self.recv()
            if report > 0 and count >= next_report:
                print("count", count, self.stats.summary())
                next_report += report
            count += self.batchsize(result)
            yield result

    def __iter__(self):
        """Receive data through an iterator"""
        return self.items()

    def write(self, data):
        """Alias for send."""
        self.send(data)

    def __len__(self):
        """Returns the value of `epoch` given at initialization.

        This allows the Connection object to be used directly as a dataloader
        and communicates the epoch size to frameworks that need it.
        The `len`/`epoch` value is otherwise unused.
        """
        return self.epoch


# class TensorcomDataset(IterableDataset):

#     def __init__(self, urls, length=1000000):
#         self.urls = urls
#         self.length = length
#         self.con = None

#     def __iter__(self):

#         if self.con is None:
#             self.con = Connection(self.urls)

#         for i in range(self.length):
#             sample = self.con.recv()
#             yield sample

#     def __len__(self):
#         return self.length
