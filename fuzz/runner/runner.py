import socket
import logging
import select
import time

from fuzz.const import TEEZZ_CMD
from fuzz.utils import u32, u64, p32

log = logging.getLogger(__name__)
log.setLevel(logging.ERROR)


class RunnerException(Exception):
    pass


class RunnerStatus:
    EXECUTOR_SUCCESS = 42
    EXECUTOR_ERROR = 1
    EXECUTOR_TIMEOUT = 2


class Runner:
    def __init__(self, host, port, session_meta) -> None:
        self._host = host
        self._port = port
        self._session_meta = session_meta
        self._terminate = False

    def _connect(self):
        self.socket = socket.socket()
        self.socket.connect((self._host, self._port))
        self.socket.settimeout(10.0)

    def _disconnect(self):
        self.socket.close()

    def __enter__(self):
        self._connect()
        msg = (
            TEEZZ_CMD.TEEZZ_CMD_START
            + p32(len(self._session_meta.serialize()))
            + self._session_meta.serialize()
        )
        self.socket.sendall(msg)
        return self

    def __exit__(self, *_):
        try:
            msg = TEEZZ_CMD.TEEZZ_CMD_END + p32(0)
            self.socket.sendall(msg)
        except BrokenPipeError as e:
            log.warn(e)
        self._disconnect()

    def terminate(self):
        self._connect()
        msg = TEEZZ_CMD.TEEZZ_CMD_TERMINATE + p32(0)
        self.socket.sendall(msg)
        self._disconnect()

    def _recv_exact(self, sz):
        out = b""
        self.socket.setblocking(0)
        tstart = time.time()
        while len(out) != sz:
            if tstart + 10.0 < time.time():
                raise socket.timeout()
            ready = select.select([self.socket], [], [], 10)
            if ready[0]:
                out += self.socket.recv(sz - len(out))
        return out

    def _recv_chunk(self):
        """returns a chunk of data sent from remote."""
        # receive the size
        content = b""
        sz_raw = self._recv_exact(4)
        sz = u32(sz_raw)
        # log.debug(f"Receiving chunk of size {sz}")

        if sz > 0:
            content = self._recv_exact(sz)
        assert len(content) == sz, "recv too short"
        return content

    def run(self, inp):
        """Runs `inp` and returns `status` and `outp`"""
        self.socket.setblocking(1)
        msg = TEEZZ_CMD.TEEZZ_CMD_SEND + p32(len(inp)) + inp
        log.debug(f"---> {len(msg)} bytes.")
        self.socket.sendall(msg)

        # first, receive the 4-byte status
        status = self._recv_exact(4)
        status = u32(status)
        log.debug(f"<--- status {status:#x}")

        response = b""
        if status == RunnerStatus.EXECUTOR_SUCCESS:
            log.debug("---- waiting for response")
            response = self._recv_chunk()
            log.debug(f"<--- response {len(response)} bytes")
        elif status == RunnerStatus.EXECUTOR_ERROR:
            response = None
        else:
            raise RunnerException("Target misbehaving.")

        return status, response
