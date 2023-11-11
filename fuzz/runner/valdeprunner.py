import os
import logging
import copy

from .baserunner import BaseRunner
from fuzz.runner.runner import RunnerStatus
from fuzz.seed.seedsequence import SeedSequence
from fuzz.runner.seqrunner import SequenceRunner
from fuzz.utils import mkdir_p

log = logging.getLogger(__name__)


class ValDepRunner(BaseRunner):
    def __init__(
        self, target_tee, port, config, in_dir, out_dir, device_id=None, reboot=False
    ):
        super(ValDepRunner, self).__init__(
            target_tee, port, config, out_dir, device_id, reboot
        )

        self._in_dir = in_dir
        self._seed_idx = 0
        self._seeds = [os.path.join(self._in_dir, d) for d in os.listdir(self._in_dir)]
        self._seeds.sort()

    def _store_seedseq(self, seedseq, storage_dir):
        mkdir_p(storage_dir)
        seedseq.store_sequence(storage_dir)

    def _probe(self, seq):
        """Runs the call sequence `seq` and collects the status codes for each
        call in the sequence. Returns an ordered list of status codes
        corresponding to the calls."""

        try:
            status = self._seqrunner.run(self._runner, seq)
        except ConnectionRefusedError as e:
            log.warning(e)
            import ipdb

            ipdb.set_trace()
        except Exception as e:
            log.error(e)
            import traceback

            traceback.print_exc()
            import ipdb

            ipdb.set_trace()

        if status != RunnerStatus.EXECUTOR_SUCCESS:
            import ipdb

            ipdb.set_trace()

        return self._seqrunner.seq_status_codes

    def run(self):
        """Run value dependency probing."""

        log.info(f"Probing value dependencies of {len(self._seeds)} seed sequences.")

        while self._seed_idx < len(self._seeds):
            log.info(f"Current seed: {self._seeds[self._seed_idx]}")
            self.current_seq = SeedSequence.load_sequence(
                self._get_seed_class(self._target_tee), self._seeds[self._seed_idx]
            )
            self._seed_idx += 1
            if len(self.current_seq) == 0:
                continue

            # copy initial sequence and obtain status codes for each call
            probe_seq = copy.deepcopy(self.current_seq)
            original_status_codes = self._probe(probe_seq)

            # obtain value dependencies for the sequence and iteratively remove
            # value dependencies.
            val_deps = self.current_seq._seed_deps.get_value_dependencies()
            num_removed_valdeps = 0
            for vd in val_deps:
                prev_probe_seq = copy.deepcopy(self.current_seq)
                probe_seq._seed_deps.remove_value_dependency(vd)
                status_codes = self._probe(probe_seq)
                if status_codes != original_status_codes:
                    # if the status codes differ, we removed a required val dep.
                    # restore the prior sequence here
                    probe_seq = prev_probe_seq
                    continue
                num_removed_valdeps += 1
            log.info(f"Removed {num_removed_valdeps} value deps.")
            seq_dir = os.path.join(
                self._out_dir, "seeds", os.path.basename(probe_seq._dir)
            )
            self._store_seedseq(probe_seq, seq_dir)

            # self.reset_device()

            # spin up the executor again
            # self._executor = AdbOrchestrator(self._target_tee, self._port,
            #                                    self._device_id,
            #                                    self._out_dir)

            # connect the sequence runner again
            self._seqrunner = SequenceRunner("127.0.0.1", self._port)
        return
