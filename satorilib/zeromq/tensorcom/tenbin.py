import numpy as np
import struct
from numpy import ndarray


def bytelen(a):
    """Determine the length of a in bytes."""
    if hasattr(a, "nbytes"):
        return a.nbytes
    elif isinstance(a, (bytearray, bytes)):
        return len(a)
    else:
        raise ValueError(a, "cannot determine nbytes")


def bytedata(a):
    """Return a the raw data corresponding to a."""
    if isinstance(a, (bytearray, bytes, memoryview)):
        return a
    elif hasattr(a, "data"):
        return a.data
    else:
        raise ValueError(a, "cannot return bytedata")


# tables for converting between long/short NumPy dtypes

long_to_short = """
float16 f2
float32 f4
float64 f8
int8 i1
int16 i2
int32 i4
int64 i8
uint8 u1
uint16 u2
unit32 u4
uint64 u8
""".strip()
long_to_short = [x.split() for x in long_to_short.split("\n")]
long_to_short = {x[0]: x[1] for x in long_to_short}
short_to_long = {v: k for k, v in long_to_short.items()}
long_to_short


def check_acceptable_input_type(data, allow64):
    for a in data:
        assert a.dtype.name in long_to_short, a.dtype.name
        if not allow64:
            assert a.dtype.name not in ["float64", "int64", "uint64"]


def str64(s):
    """Convert a string to an int64."""
    s = s + "\0" * (8 - len(s))
    s = s.encode("ascii")
    return struct.unpack("@q", s)[0]


def unstr64(i):
    """Convert an int64 to a string."""
    b = struct.pack("@q", i)
    return b.decode("ascii").strip("\0")


def check_infos(data, infos, required_infos=None):
    """Implement infos verification logic."""
    if required_infos is False or required_infos is None:
        return data
    if required_infos is True:
        return data, infos
    assert isinstance(required_infos, (tuple, list))
    for required, actual in zip(required_infos, infos):
        assert required == actual, (required, actual)
    return data


def encode_header(a, info=""):
    """Encode an array header as a byte array."""
    assert a.ndim < 10
    assert a.nbytes == np.prod(a.shape) * a.itemsize
    assert a.dtype.name in long_to_short
    header = [str64(long_to_short[a.dtype.name]), str64(info), len(a.shape)] + list(
        a.shape
    )
    return bytedata(np.array(header, dtype="i8"))


def decode_header(h):
    """Decode a byte array into an array header."""
    h = np.frombuffer(h, dtype="i8")
    assert unstr64(h[0]) in short_to_long, h
    dtype = np.dtype(short_to_long[unstr64(h[0])])
    info = unstr64(h[1])
    rank = int(h[2])
    shape = tuple(h[3:3 + rank])
    return shape, dtype, info


def encode_list(l, infos=None):
    """Given a list of arrays, encode them into a list of byte arrays."""
    if infos is None:
        infos = [""]
    else:
        assert len(l) == len(infos)
    result = []
    for i, a in enumerate(l):
        header = encode_header(a, infos[i % len(infos)])
        result += [header, bytedata(a)]
    return result


def decode_list(l, infos=False):
    """Given a list of byte arrays, decode them into arrays."""
    result = []
    infos0 = []
    for header, data in zip(l[::2], l[1::2]):
        shape, dtype, info = decode_header(header)
        a = np.frombuffer(data, dtype=dtype, count=np.prod(shape)).reshape(*shape)
        result += [a]
        infos0 += [info]
    return check_infos(result, infos0, infos)


magic_str = "~TenBin~"
magic = str64(magic_str)
magic_bytes = unstr64(magic).encode("ascii")


def roundup(n, k=64):
    """Round up to the next multiple of 64."""
    return k * ((n + k - 1) // k)


def encode_chunks(l):
    """Encode a list of chunks into a single byte array, with lengths and magics.."""
    size = sum(16 + roundup(b.nbytes) for b in l)
    result = bytearray(size)
    offset = 0
    for b in l:
        result[offset:offset + 8] = magic_bytes
        offset += 8
        result[offset:offset + 8] = struct.pack("@q", b.nbytes)
        offset += 8
        result[offset:offset + bytelen(b)] = b
        offset += roundup(bytelen(b))
    return result


def decode_chunks(buf):
    """Decode a byte array into a list of chunks."""
    result = []
    offset = 0
    total = bytelen(buf)
    while offset < total:
        assert magic_bytes == buf[offset:offset + 8]
        offset += 8
        nbytes = struct.unpack("@q", buf[offset:offset + 8])[0]
        offset += 8
        b = buf[offset:offset + nbytes]
        offset += roundup(nbytes)
        result.append(b)
    return result


def encode_buffer(l, infos=None):
    """Encode a list of arrays into a single byte array."""
    return encode_chunks(encode_list(l, infos=infos))


def decode_buffer(buf, infos=False):
    """Decode a byte array into a list of arrays."""
    return decode_list(decode_chunks(buf), infos=infos)


def write_chunk(stream, buf):
    """Write a byte chunk to the stream with magics, length, and padding."""
    nbytes = bytelen(buf)
    stream.write(magic_bytes)
    stream.write(struct.pack("@q", nbytes))
    stream.write(bytedata(buf))
    padding = roundup(nbytes) - nbytes
    if padding > 0:
        stream.write(b"\0" * padding)


def read_chunk(stream):
    """Read a byte chunk from a stream with magics, length, and padding."""
    magic = stream.read(8)
    if magic == b"":
        return None
    assert magic == magic_bytes, (magic, magic_bytes)
    nbytes = stream.read(8)
    nbytes = struct.unpack("@q", nbytes)[0]
    assert nbytes >= 0
    data = stream.read(nbytes)
    padding = roundup(nbytes) - nbytes
    if padding > 0:
        stream.read(padding)
    return data


def write(stream, l, infos=None):
    """Write a list of arrays to a stream, with magics, length, and padding."""
    for chunk in encode_list(l, infos=infos):
        write_chunk(stream, chunk)


def read(stream, n=999999, infos=False):
    """Read a list of arrays from a stream, with magics, length, and padding."""
    chunks = []
    for i in range(n):
        header = read_chunk(stream)
        if header is None:
            break
        data = read_chunk(stream)
        assert data is not None
        chunks += [header, data]
    return decode_list(chunks, infos=infos)


def save(fname, *args, infos=None, nocheck=False):
    """Save a list of arrays to a file, with magics, length, and padding."""
    if not nocheck:
        assert fname.endswith(".ten")
    with open(fname, "wb") as stream:
        write(stream, args, infos=infos)


def load(fname, infos=False, nocheck=False):
    """Read a list of arrays from a file, with magics, length, and padding."""
    if not nocheck:
        assert fname.endswith(".ten")
    with open(fname, "rb") as stream:
        return read(stream, infos=infos)


def zsend_single(socket, l, infos=None):
    """Send arrays as a single part ZMQ message."""
    return socket.send(encode_buffer(l, infos=infos))


def zrecv_single(socket, infos=False, flags=0):
    """Receive arrays as a single part ZMQ message."""
    return decode_buffer(socket.recv(flags=flags), infos=infos)


def zsend_multipart(socket, l, infos=None):
    """Send arrays as a multipart ZMQ message."""
    return socket.send_multipart(encode_list(l, infos=infos))


def zrecv_multipart(socket, infos=False, flags=0):
    """Receive arrays as a multipart ZMQ message."""
    return decode_list(socket.recv_multipart(flags=flags), infos=infos)


def sctp_send(socket, dest, l, infos=None):
    """Send arrays as an SCTP datagram.

    This is just a convenience function and illustration.
    For more complex networking needs, you may want
    to call encode_buffer and sctp_send directly.
    """
    socket.sctp_send(bytes(encode_buffer(l, infos=infos)), to=dest)


def sctp_recv(socket, infos=False, maxsize=100000000):
    """Receive arrays as an SCTP datagram.

    This is just a convenience function and illustration.
    For more complex networking needs, you may want
    to call sctp_recv and decode_buffer directly.
    """
    client, _ = socket.accept()
    _, _, data, _ = client.sctp_recv(maxsize)
    return decode_buffer(data, infos=infos)
