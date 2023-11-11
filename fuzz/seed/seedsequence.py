from __future__ import annotations
import os
import pickle
import logging

from fuzz.utils import mkdir_p
from fuzz.seed.seed import Seed
from fuzz.apidependency import IoctlCallSequence

from typing import List, Optional


log = logging.getLogger(__name__)


class SeedSequence:
    def __init__(
        self, seeds: List[Seed], seed_deps: Optional[IoctlCallSequence] = None
    ):
        self._idx = 0
        self._seeds: List[Seed] = seeds
        self._seed_deps = seed_deps
        self._dir = None
        if self._seed_deps:
            assert len(self._seeds) == len(
                self._seed_deps
            ), "seeds vs seed deps mismatch"

    @classmethod
    def load_sequence(cls, seed_translator_cls, path: str) -> SeedSequence:
        # load seeds from fs and sort them
        seed_paths = [
            os.path.join(path, d) for d in os.listdir(path) if "pickle" not in d
        ]

        seeds: List[Seed] = []
        for seed_path in seed_paths:
            seed = Seed.load_seed(seed_translator_cls, seed_path)
            seeds.append(seed)

        seeds.sort(key=lambda o: o._id)

        dependencies_path = os.path.join(path, "dependencies.pickle")
        if os.path.exists(dependencies_path):
            # load value dependency file
            with open(dependencies_path, "rb") as f:
                seed_deps = pickle.load(f)
        else:
            seed_deps = None

        # create `SeedSequence`
        seed_sequence = cls(seeds, seed_deps)
        seed_sequence._dir = path

        return seed_sequence

    def store_sequence(self, path: str):
        for idx, seed in enumerate(self._seeds):
            seed_dir = os.path.join(path, str(idx))
            mkdir_p(seed_dir)
            seed.store_seed(seed_dir)

        if self._seed_deps:
            assert len(self._seeds) == len(
                self._seed_deps
            ), "seeds vs seed deps mismatch"
            with open(os.path.join(path, "dependencies.pickle"), "wb") as f:
                pickle.dump(self._seed_deps, f)

    def __iter__(self):
        self._idx = 0
        return self

    def __len__(self):
        return len(self._seeds)

    def __getitem__(self, key: int) -> Seed:
        return self._seeds[key]

    def _satisfy(self) -> None:
        if not self._seed_deps:
            return

        call = self._seed_deps[self._idx]
        base = self._seed_deps[0].dump_id

        if not call.value_dependencies:
            return

        try:
            for valdep in call.value_dependencies:
                src_idx = valdep.src_ioctl_call.dump_id - base
                if len(self._seeds) <= src_idx:
                    # TODO
                    log.warning("indexing here is screwed, fix this!")
                    import ipdb

                    ipdb.set_trace()
                    return
                src_seed = self._seeds[src_idx]

                if not src_seed.output.is_success():
                    return

                dst_seed = self._seeds[self._idx]
                src_seed.output.resolve(dst_seed.input, valdep)
        except Exception as e:
            import ipdb

            ipdb.set_trace()

    def __next__(self) -> Seed:
        if self._idx < len(self._seeds):
            self._satisfy()
            elem = self._seeds[self._idx]
            self._idx += 1
            return elem
        else:
            raise StopIteration
