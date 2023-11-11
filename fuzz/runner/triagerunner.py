import logging
import signal

from .baserunner import BaseRunner
from fuzz.seed.seedsequence import SeedSequence

log = logging.getLogger(__name__)


class TriageRunnerException(Exception):
    pass


class TriageRunner(BaseRunner):
    """A runner aimed at reproducing crashing sequences."""

    def __init__(self, target_tee, port, config, out_dir, device_id=None, reboot=False):
        super(TriageRunner, self).__init__(
            target_tee, port, config, out_dir, device_id, reboot
        )

    def run(self, crash_seq):
        """run triage"""
        self.current_seq = crash_seq

        def sig_handler(signum, frame):
            raise TriageRunnerException("Target not responding.")

        # signal.signal(signal.SIGALRM, sig_handler)
        # signal.alarm(300)
        # try:
        self._seqrunner.run(self._runner, self.current_seq)
        # except TriageRunnerException as e:
        #     log.warning("Timeout")
        # signal.alarm(0)

        if self._seqrunner.crashed():
            log.debug("Crash reprocuded")

        return

    def _terminate(self):
        # self._runner.terminate()
        del self._seqrunner
        return

    def triage(self, crash_seq_dir):
        crash_seq = SeedSequence.load_sequence(
            self._get_seed_class(self._target_tee), crash_seq_dir
        )
        self.run(crash_seq)
        self._terminate()
        return
