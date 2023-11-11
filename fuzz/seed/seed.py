from __future__ import annotations
import os

from fuzz.utils import mkdir_p


class Seed(object):
    def __init__(self, seed_translator_cls, id, input, output):
        self.seed_translator_cls = seed_translator_cls
        self._id = id
        self.input = input
        self.output = output

    @classmethod
    def load_seed(cls, seed_translator_cls, path: str) -> Seed:
        id = int(os.path.basename(path))
        input_path = os.path.join(path, "onenter")
        output_path = os.path.join(path, "onleave")
        input = seed_translator_cls.deserialize_raw_from_path(input_path)
        output = seed_translator_cls.deserialize_raw_from_path(output_path)
        return cls(seed_translator_cls, id, input, output)

    def store_seed(self, path: str) -> None:
        input_path = os.path.join(path, "onenter")
        output_path = os.path.join(path, "onleave")
        mkdir_p(input_path)
        mkdir_p(output_path)
        self.input.serialize_to_path(input_path)
        self.output.serialize_to_path(output_path)
        return
