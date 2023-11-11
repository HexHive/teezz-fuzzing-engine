from __future__ import annotations
import os
import datetime
import json
import logging
import random
import copy
import time

from .baserunner import BaseRunner
from fuzz.runner.seqrunner import SequenceRunner
from fuzz.runner.runner import RunnerStatus
from fuzz.seed.seedsequence import SeedSequence
from fuzz.seed.seed import Seed
from fuzz.utils import mkdir_p
from fuzz.orchestrator.adborchestrator import AdbOrchestrator
from fuzz.stats import STATS
from fuzz.mutation.seedsequencemutator import SeedSequenceMutator
from fuzz.mutation.templatemutator import TemplateMutator

from adb import adb

from typing import List, Set, Tuple, Any

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class FuzzRunnerException(Exception):
    pass


class FuzzRunner(BaseRunner):
    def __init__(
        self,
        target_tee,
        port,
        config,
        in_dir,
        out_dir,
        mutation_engine,
        modelaware,
        device_id=None,
        reboot=False,
        cov_enabled=False,
    ):
        super(FuzzRunner, self).__init__(
            target_tee, port, config, out_dir, device_id, reboot
        )

        # check config file for path to protobuf and create mutation engine
        self.engine = mutation_engine
        self.modelaware = modelaware
        self._cov_enabled = cov_enabled
        # TODO
        self._mutator = TemplateMutator(self._config["proto"])

        self._in_dir = in_dir
        self._seed_idx = 0
        self._seeds = [
            os.path.join(self._in_dir, d) for d in os.listdir(self._in_dir)
        ]
        self._seeds.sort()

        self._is_seeding = True
        self._population: List[SeedSequence] = []
        self._coverages_seen: Set[Tuple[Any]] = set()
        self._timeout_ctr = 0
        self._prev_run_timed_out = False
        self._needs_reset = False

        # time based fuzzing
        self._start_time = datetime.datetime.now()
        self._elapsed_prev_run = datetime.timedelta(seconds=0)

        self.event_log = []

        # event logs go to this file
        self.event_log_path = os.path.join(self._out_dir, "event.log")
        self._stats_path = os.path.join(self._out_dir, "stats.json")
        self._cfg_path = os.path.join(self._out_dir, "fuzz.cfg")
        self._save_campaign_config()
        self._load_stats()

    def _load_stats(self):
        if os.path.isfile(self._stats_path):
            with open(self._stats_path, "r") as f:
                stats = json.load(f)
            STATS["#sequences"] = stats["#sequences"]
            STATS["#interactions"] = stats["#interactions"]
            STATS["#successes"] = stats["#successes"]
            STATS["#errors"] = stats["#errors"]
            STATS["#timeouts"] = stats["#timeouts"]
            STATS["#crashtimeouts"] = stats["#crashtimeouts"]
            STATS["#factoryresets"] = stats["#factoryresets"]
            STATS["#hardresets"] = stats["#hardresets"]
            STATS["#resets"] = stats["#resets"]
            STATS["#crashes"] = stats["#crashes"]
            STATS["#newcov"] = stats["#newcov"]
            STATS["#ta_successes"] = stats["#ta_successes"]
            STATS["#ta_fails"] = stats["#ta_fails"]
            self._elapsed_prev_run = datetime.timedelta(
                seconds=stats["elapsed_time"]
            )
            # decode list of lists to set of tuples again
            self._coverages_seen = set([tuple(t) for t in stats["cov_seen"]])

    def get_stats(self):
        return {
            "#sequences": STATS["#sequences"],
            "#interactions": STATS["#interactions"],
            "#successes": STATS["#successes"],
            "#errors": STATS["#errors"],
            "#timeouts": STATS["#timeouts"],
            "#crashtimeouts": STATS["#crashtimeouts"],
            "#hardresets": STATS["#hardresets"],
            "#factoryresets": STATS["#factoryresets"],
            "#resets": STATS["#resets"],
            "#crashes": STATS["#crashes"],
            "#newcov": STATS["#newcov"],
            "#ta_successes": STATS["#ta_successes"],
            "#ta_fails": STATS["#ta_fails"],
        }

    def print_stats(self):
        log.info(self.get_stats())

    def _save_stats(self, elapsed_time: int):
        stats = self.get_stats()
        stats["elapsed_time"] = elapsed_time
        # encode set of tuples to list of list to make it digestible for JSON
        stats["cov_seen"] = list(self._coverages_seen)
        with open(self._stats_path, "w") as f:
            f.write(json.dumps(stats))

    def _save_campaign_config(self):
        self._config["device_id"] = self._device_id
        self._config["port"] = self._port
        self._config["mutation"] = self.engine
        self._config["modelaware"] = self.modelaware
        with open(self._cfg_path, "w") as f:
            f.write(json.dumps(self._config))

    def _create_candidate(self) -> SeedSequence:

        if not self._population:
            raise FuzzRunnerException("No seed candidates.")

        # we randomly choose a member of the populaton (a `SeedSequence`)
        seedseq = copy.deepcopy(random.choice(self._population))

        assert (
            len(seedseq) != 0
        ), "The SeedSequence should contain at lest one interaction"

        if len(seedseq) > 1 and random.random() < 0.1:
            # mutate the sequence metadata only if we have more than 1
            # interaction
            for _ in range(random.randrange(1, len(seedseq))):
                SeedSequenceMutator.mutate(seedseq)

        # make the number of mutations dependent on the length of the sequence
        nmutations = random.randint(1, len(seedseq))
        log.info(f"Mutating current SeedSequence {nmutations} times.")
        for _ in range(nmutations):
            seed: Seed = random.choice(seedseq)
            if random.random() < 0.1:
                # 10% chance to mutate metadata
                seed.input.mutate(self._mutator.mutate)

            # we pick exactly one parameter of this `Seed` that we mutate
            # TODO: we might choose NONE params here that will not be mutated.
            param = random.choice(seed.input.params)
            param.mutate(self._mutator.mutate)

        return seedseq

    def fuzz(self) -> SeedSequence:
        if self._seed_idx < len(self._seeds):
            log.info(f"Current seed: {self._seeds[self._seed_idx]}")
            # seeding
            candidate = SeedSequence.load_sequence(
                self._get_seed_class(self._target_tee),
                self._seeds[self._seed_idx],
            )
            self._seed_idx += 1
        else:
            self._is_seeding = False
            # mutating
            candidate = self._create_candidate()
        return candidate

    def _add_seed(self, seedseq: SeedSequence) -> None:
        self._population.append(seedseq)
        t = int(self.elapsed_time().total_seconds())
        name = f"id:{self._queue_id:08d},time:{t:08d}"
        seq_dir = os.path.join(self._queue_dir, name)
        self._store_seedseq(seedseq, seq_dir)
        self._queue_id += 1

    def _add_crash(self, seedseq: SeedSequence):
        t = int(self.elapsed_time().total_seconds())
        name = f"id:{self._crash_id:08d},time:{t:08d}"
        seq_dir = os.path.join(self._crashes_dir, name)
        self._store_seedseq(seedseq, seq_dir)
        self._crash_id += 1

    def _add_timeout(self, seedseq: SeedSequence):
        t = int(self.elapsed_time().total_seconds())
        name = f"id:{self._hang_id:08d},time:{t:08d}"
        seq_dir = os.path.join(self._timeouts_dir, name)
        self._store_seedseq(seedseq, seq_dir)
        self._hang_id += 1

    def _add_cov(self, seedseq: SeedSequence):
        h = f"id:{self._cov_id:08d}"
        h += f",time:{int(self.elapsed_time().total_seconds()):08d}"
        h += f",seq:{self._seqrunner.total_seqs:06d}"
        h += f",run:{self._seqrunner.total_runs:08d}"
        seq_dir = os.path.join(self._cov_dir, h)
        self._store_seedseq(seedseq, seq_dir)
        self._cov_id += 1

    def _store_seedseq(self, seedseq: SeedSequence, storage_dir: str):
        mkdir_p(storage_dir)
        seedseq.store_sequence(storage_dir)

    def run(self):
        """run fuzzer"""
        self.current_seq = self.fuzz()

        timed_out = False

        def sig_handler(signum, frame):
            raise FuzzRunnerException("Target not responding.")

        # signal.signal(signal.SIGALRM, sig_handler)
        # signal.alarm(300)
        try:
            status = self._seqrunner.run(self._runner, self.current_seq)
        except ConnectionRefusedError as e:
            log.warning(e)
            status = RunnerStatus.EXECUTOR_TIMEOUT
        except Exception as e:
            log.error(e)
            import traceback

            traceback.print_exc()
            import ipdb

            ipdb.set_trace()
            status = RunnerStatus.EXECUTOR_TIMEOUT

        # we need this for the coverage available on optee
        if self._cov_enabled and status == RunnerStatus.EXECUTOR_SUCCESS:
            forkserver_status = self._seqrunner.forkserver_status()
            log.info(f"frksvr: {forkserver_status}")
            if forkserver_status:
                self._add_cov(self.current_seq)
        # signal.alarm(0)

        if status == RunnerStatus.EXECUTOR_TIMEOUT:
            if self._device_id and not adb.is_device_present(self._device_id):
                # the device likely rebooted due to a crash
                STATS["#crashtimeouts"] += 1
                self._needs_reset = True
                self._add_timeout(self.current_seq)

            if self._prev_run_timed_out:
                self._timeout_ctr += 1
                time.sleep(5)
            else:
                self._timeout_ctr = 1

            if self._timeout_ctr == 5:
                self._timeout_ctr = 0
                self._needs_reset = True
            self._prev_run_timed_out = True
            return

        if status != RunnerStatus.EXECUTOR_SUCCESS:
            return

        elif self._seqrunner.crashed():
            log.debug("Crash")
            STATS["#crashes"] += 1
            self._add_crash(self.current_seq)
        elif self._is_seeding or self._seqrunner.coverage().difference(
            self._coverages_seen
        ):
            # update coverage and add seed when
            # 1) we're still seeding, or
            # 2) we have not seen this coverage before
            self._coverages_seen.update(self._seqrunner.coverage())
            log.debug("Appending")
            STATS["#newcov"] += 1
            self._add_seed(self.current_seq)

        self._prev_run_timed_out = False
        return

    def _terminate(self):
        self._runner.terminate()
        del self._seqrunner
        return

    def runs(self, n):
        # try:
        for _ in range(n):
            self.run()
        # self._terminate()
        # except KeyboardInterrupt:
        #    self._terminate()
        # return

    def elapsed_time(self):
        return (
            datetime.datetime.now() - self._start_time
        ) + self._elapsed_prev_run

    def _target_needs_reset(self):
        if self._device_id is None:
            # we do not reset non-adb devices for now
            return False
        if self._needs_reset:
            self._needs_reset = False
            return True
        return self._seqrunner.total_runs > 500

    def _seed(self):
        self._seeding_start = datetime.datetime.now()
        try:
            while self._is_seeding:
                self.run()
                self.print_stats()
        except KeyboardInterrupt:
            self._terminate()
        self._seeding_end = datetime.datetime.now()
        self._seeding_duration = self._seeding_end - self._seeding_start
        log.info(
            f"Seeding finished after {self._seeding_duration.total_seconds()}"
        )

        with open(os.path.join(self._out_dir, "seeding_done"), "w") as f:
            f.write(str(self._seeding_duration.total_seconds()))

    def _load_queue(self) -> None:

        # load seeds stored in `self._queue_dir` from previous run
        q_entries = [
            os.path.join(self._queue_dir, e)
            for e in os.listdir(self._queue_dir)
        ]
        for q_entry in q_entries:
            candidate = SeedSequence.load_sequence(
                self._get_seed_class(self._target_tee), q_entry
            )
            self._population.append(candidate)
            self._seed_idx += 1
        self._is_seeding = False

    def runt(self, duration: int) -> None:
        """Run fuzzer for `duration` seconds.

        Args:
            duration (int): duration in seconds
        """

        log.info(f"Starting fuzzer for {duration} seconds.")

        if self._elapsed_prev_run.total_seconds() > 0:
            # continue a previous run
            self._load_queue()
        else:
            self._seed()

        d = datetime.timedelta(seconds=(duration))

        fuzz_rounds = 0
        # try:
        while d.total_seconds() > self.elapsed_time().total_seconds():
            t_remaining = (
                d.total_seconds() - self.elapsed_time().total_seconds()
            )
            t1 = datetime.datetime.now()
            if self._target_needs_reset():
                STATS["#resets"] += 1
                self.reset_device()
                # spin up the executor again
                self._executor = AdbOrchestrator(
                    self._target_tee, self._port, self._device_id, self._out_dir
                )
                # connect the sequence runner again
                self._seqrunner = SequenceRunner("127.0.0.1", self._port)

            self.run()
            t2 = datetime.datetime.now()
            tdiff = t2 - t1
            fuzz_rounds += 1
            log.info(
                f"#{fuzz_rounds}: Sequence (len={len(self.current_seq)}) took {tdiff.total_seconds()}"
            )
            self.print_stats()
            log.info(f"time remaining: {t_remaining}")
            self._save_stats(self.elapsed_time().total_seconds())
        self._terminate()
        # except KeyboardInterrupt:
        #    self._terminate()
        # except Exception as e:
        #    import ipdb
        #    ipdb.set_trace()

        log.info(
            f"Fuzzing finished after {self.elapsed_time().total_seconds()}"
        )
        return
