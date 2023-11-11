import logging
import socket
from fuzz.utils import u32
from fuzz.runner.runner import RunnerStatus, Runner
from fuzz.stats import STATS

from ..seed.seedsequence import SeedSequence

log = logging.getLogger(__file__)
log.setLevel(logging.ERROR)

from typing import Set, Tuple, Any


class SequenceRunner(object):
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._coverage: Set[Tuple[Any]] = set()
        self._crashed = False
        self.seq_status_codes = []
        self._total_seqs = 0
        self._total_runs = 0
        # `True` if status codes of recorded seq responses matches status codes
        # of observed seq responses, `False` otherwise
        self._seq_replayable = True

        self._socket = socket.socket()
        self._socket.connect((self._host, self._port))

    def __del__(self):
        self._socket.close()

    def _recv_exact(self, sz: int):
        out = b""
        while len(out) != sz:
            out += self._socket.recv(1)
        return out

    @property
    def total_runs(self):
        return self._total_runs

    @property
    def total_seqs(self):
        return self._total_seqs

    def forkserver_status(self):
        return u32(self._recv_exact(4))

    def coverage(self) -> Set[Tuple[Any]]:
        return self._coverage

    def crashed(self):
        return self._crashed

    def run(self, runner: Runner, seedseq: SeedSequence):
        assert len(seedseq) > 0, "No seeds"
        self._total_seqs += 1
        self._coverage = set()
        self.seq_status_codes = []  #  reset status codes
        self._crashed = False
        self._seq_replayable = True
        STATS["#sequences"] += 1

        # the `__enter__()` and `__exit__()` methods of the runner are
        # responsible for opening and closing the connection to the executor
        # on the device.
        with runner:
            # the `__next__()` method of the `SeedSequence` iterator object
            # takes care of resolving value dependencies if present in this seq
            for idx, seed in enumerate(seedseq):
                self._total_runs += 1
                inp = seed.input.serialize()

                # TODO: remove when missing input buffer for input memref types
                # is fixed.
                if not inp:
                    continue

                try:
                    STATS["#interactions"] += 1
                    status, response = runner.run(inp)
                except socket.timeout:
                    STATS["#timeouts"] += 1
                    log.warn("Timeout")
                    status = RunnerStatus.EXECUTOR_TIMEOUT
                except ConnectionResetError as e:
                    STATS["#errors"] += 1
                    log.warn(e)
                    status = RunnerStatus.EXECUTOR_ERROR

                if status == RunnerStatus.EXECUTOR_SUCCESS:
                    STATS["#successes"] += 1

                    self.seq_status_codes.append(seed.output.status_code)
                    prev_out = seed.output
                    prev_is_success = prev_out.is_success()

                    seed.output = seed.input.deserialize_obj(response)
                    if seed.output.is_success() != prev_is_success:
                        self._seq_replayable = False

                    self._coverage.add(seed.output.coverage)
                    if seed.output.is_success():
                        STATS["#ta_successes"] += 1
                    else:
                        STATS["#ta_fails"] += 1

                    if seed.output.is_crash():
                        # import ipdb
                        # ipdb.set_trace()
                        self._crashed = True
                        break
                else:
                    self.seq_status_codes.append(None)
                    STATS["#errors"] += 1
                    # break if runner failed
                    break
        return status
