"""This module provides the basic support for asynchronous communication and
computation of secret-shared values.
"""

import struct
import itertools
import functools
import typing
from asyncio import Protocol, Future
from mpyc.sectypes import Share

runtime = None


class SharesExchanger(Protocol):
    """Send and receive shares.

    Bidirectional connection with one of the other parties (peers).
    """

    def __init__(self, peer_pid=None):
        self.peer_pid = peer_pid
        self.bytes = bytearray()
        self.buffers = {}
        self.transport = None

    def _key_transport_done(self):
        runtime.parties[self.peer_pid].protocol = self
        if all(p.protocol is not None for p in runtime.parties):
            runtime.parties[runtime.pid].protocol.set_result(runtime)

    def connection_made(self, transport):
        """Called when a connection is made.

        If the party is a client for this connection, it sends its identity
        to the peer as well as any PRSS keys.
        """
        self.transport = transport
        if self.peer_pid is not None:  # party is client (peer is server)
            m = len(runtime.parties)
            t = runtime.threshold
            pid_keys = str(runtime.pid).encode()  # send pid
            for subset in itertools.combinations(range(m), m - t):
                if self.peer_pid in subset and runtime.pid == min(subset):
                    pid_keys += runtime._prss_keys[subset]  # send PRSS keys
            transport.write(pid_keys)
            self._key_transport_done()

    def send_data(self, pc, payload):
        """Send payload labeled with pc to the peer.

        Message format consists of four parts:
         1. pc_size (2 bytes)
         2. payload_size (4 bytes)
         3. pc (pc_size 4-byte ints)
         4. payload (byte string of length payload_size).
        """
        pc_size, payload_size = len(pc), len(payload)
        fmt = f'!HI{pc_size}I{payload_size}s'
        t = (pc_size, payload_size) + pc + (payload,)
        self.transport.write(struct.pack(fmt, *t))

    def data_received(self, data):
        """Called when data is received from the peer.

        Received bytes are unpacked as a program counter and the payload
        (actual data). The payload is passed to the appropriate Future, if any.

        First message from peer is processed differently if peer is a client.
        """
        self.bytes.extend(data)
        if self.peer_pid is None:  # peer is client (party is server)
            peer_pid = int(self.bytes[:1])
            len_packet = 1
            m = len(runtime.parties)
            t = runtime.threshold
            for subset in itertools.combinations(range(m), m - t):
                if runtime.pid in subset and peer_pid == min(subset):
                    len_packet += 16
            if len(self.bytes) < len_packet:
                return
            # record new protocol peer
            self.peer_pid = peer_pid
            # store keys received from peer
            len_packet = 1
            for subset in itertools.combinations(range(m), m - t):
                if runtime.pid in subset and peer_pid == min(subset):
                    runtime._prss_keys[subset] = self.bytes[len_packet:len_packet + 16]
                    len_packet += 16
            del self.bytes[:len_packet]
            self._key_transport_done()

        while self.bytes:
            if len(self.bytes) < 6:
                return

            pc_size, payload_size = struct.unpack('!HI', self.bytes[:6])
            len_packet = 6 + pc_size * 4 + payload_size
            if len(self.bytes) < len_packet:
                return

            fmt = f'!{pc_size}I{payload_size}s'
            unpacked = struct.unpack(fmt, self.bytes[6:len_packet])
            del self.bytes[:len_packet]
            pc = unpacked[:pc_size]
            payload = unpacked[-1]
            if pc in self.buffers:
                self.buffers.pop(pc).set_result(payload)
            else:
                self.buffers[pc] = payload

    def connection_lost(self, exc):
        pass

    def close_connection(self):
        """Close connection with the peer."""
        self.transport.close()


class _AwaitableFuture:
    """Cheap replacement of a Future."""

    __slots__ = 'value'

    def __init__(self, value):
        self.value = value

    def __await__(self):
        return self.value
        yield  # NB: makes __await__ iterable


class _SharesCounter(Future):
    """Count and gather all futures (shared values) in an object."""

    __slots__ = 'counter', 'obj'

    def __init__(self, obj):
        super().__init__(loop=runtime._loop)
        self.counter = 0
        self._add_callbacks(obj)
        if not self.counter:
            self.set_result(_get_results(obj))
        else:
            self.obj = obj

    def _decrement(self, _):
        self.counter -= 1
        if not self.counter:
            self.set_result(_get_results(self.obj))

    def _add_callbacks(self, obj):
        if isinstance(obj, Share):
            if isinstance(obj.df, Future):
                if obj.df.done():
                    obj.df = obj.df.result()
                else:
                    self.counter += 1
                    obj.df.add_done_callback(self._decrement)
        elif isinstance(obj, Future) and not obj.done():
            self.counter += 1
            obj.add_done_callback(self._decrement)
        elif isinstance(obj, (list, tuple)):
            for x in obj:
                self._add_callbacks(x)


def _get_results(obj):
    if isinstance(obj, Share):
        if isinstance(obj.df, Future):
            return obj.df.result()

        return obj.df

    if isinstance(obj, Future):
        return obj.result()

    if isinstance(obj, (list, tuple)):
        return type(obj)(map(_get_results, obj))

    return obj


def gather_shares(*obj):
    """Gather all results for the given futures (shared values)."""
    if len(obj) == 1:
        obj = obj[0]
    if obj is None:
        return _AwaitableFuture(None)

    if isinstance(obj, Future):
        return obj

    if isinstance(obj, Share):
        if isinstance(obj.df, Future):
            return obj.df

        return _AwaitableFuture(obj.df)

    if not runtime.options.no_async:
        assert isinstance(obj, (list, tuple)), obj
        return _SharesCounter(obj)

    return _AwaitableFuture(_get_results(obj))


class _Awaitable:

    __slots__ = 'value'

    def __init__(self, value):
        self.value = value

    def __await__(self):
        yield self.value


def _nested_list(rt, n, dims):
    if dims:
        n0 = dims[0]
        dims = dims[1:]
        s = [_nested_list(rt, n0, dims) for _ in range(n)]
    else:
        s = [rt() for _ in range(n)]
    return s


def returnType(*args, wrap=True):
    """Define return type for MPyC coroutines.

    Used in first await expression in an MPyC coroutine.
    """
    rettype, *dims = args
    if isinstance(rettype, type(None)):
        rettype = None
    if rettype is not None:
        if isinstance(rettype, tuple):
            stype = rettype[0]
            integral = rettype[1]
            if stype.field.frac_length:
                rt = lambda: stype(None, integral)
            else:
                rt = stype
        elif issubclass(rettype, Future):
            rt = lambda: rettype(loop=runtime._loop)
        else:
            rt = rettype
        if dims:
            rettype = _nested_list(rt, dims[0], dims[1:])
        else:
            rettype = rt()
    if wrap:
        rettype = _Awaitable(rettype)
    return rettype


class _ProgramCounterWrapper:

    __slots__ = 'coro', 'pc'

    def __init__(self, coro):
        self.coro = coro
        runtime._increment_pc()
        self.pc = (0,) + runtime._program_counter  # fork

    def __await__(self):
        while True:
            pc = runtime._program_counter
            runtime._program_counter = self.pc
            try:
                val = self.coro.send(None)
                self.pc = runtime._program_counter
            except StopIteration as exc:
                return exc.value  # NB: required for Python 3.7
            finally:
                runtime._program_counter = pc
            yield val


async def _wrap(coro):
    return await coro

pc_level = 0
"""Tracks (length of) program counter to implement barriers."""


def _reconcile(decl, givn):
    global pc_level
    pc_level -= 1
    if decl is None:
        return

    __reconcile(decl, givn)


def __reconcile(decl, givn):
    if isinstance(decl, Share):
        if isinstance(givn, Share):
            if isinstance(givn.df, Future):
                if runtime.options.no_async:
                    decl.df.set_result(givn.df.result())
                else:
                    givn.df.add_done_callback(lambda x: decl.df.set_result(x.result()))
            else:
                decl.df.set_result(givn.df)
        elif isinstance(givn, Future):
            if runtime.options.no_async:
                decl.df.set_result(givn.result())
            else:
                givn.add_done_callback(lambda x: decl.df.set_result(x.result()))
        else:
            decl.df.set_result(givn)
    elif isinstance(decl, list):
        for d, g in zip(decl, givn):
            __reconcile(d, g)
    else:  # isinstance(decl, Future)
        decl.set_result(givn)


def _ncopy(nested_list):
    if isinstance(nested_list, list):
        return list(map(_ncopy, nested_list))

    return nested_list


def _mpc_coro_no_pc(func):
    return mpc_coro(func, pc=False)


def mpc_coro(func, pc=True):
    """Decorator turning coroutine func into an MPyC coroutine.

    An MPyC coroutine is evaluated asychronously, returning empty placeholders.
    The type of the placeholders is defined either by a return annotation
    of the form "-> expression" or by the first await expression in func.
    Return annotations can only be used for static types.
    """

    rettype = typing.get_type_hints(func).get('return')

    @functools.wraps(func)
    def typed_asyncoro(*args, **kwargs):
        global pc_level
        pc_level += 1
        coro = func(*args, **kwargs)
        if rettype:
            decl = returnType(rettype, wrap=False)
        else:
            decl = coro.send(None)
        if runtime.options.no_async:
            while True:
                try:
                    coro.send(None)
                except StopIteration as exc:
                    _reconcile(decl, exc.value)
                    return decl

        if pc:
            coro = _wrap(_ProgramCounterWrapper(coro))
        d = runtime._loop.create_task(coro)  # ensure_future
        d.add_done_callback(lambda v: _reconcile(decl, v.result()))
        return _ncopy(decl)

    return typed_asyncoro