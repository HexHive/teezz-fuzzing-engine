from __future__ import annotations
import random
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

from fuzz.seed.seedsequence import SeedSequence
from fuzz.apidependency import IoctlCall


class SeedSequenceMutator:

    @staticmethod
    def mutate(seedseq: SeedSequence) -> None:
        if seedseq._seed_deps:
            ioctl: IoctlCall = random.choice(seedseq._seed_deps)

            if ioctl.value_dependencies:
                del_idx = random.randrange(0, len(ioctl.value_dependencies))
                log.debug(f"Deleting ValueDependency at idx {del_idx}")
                del ioctl.value_dependencies[del_idx]
