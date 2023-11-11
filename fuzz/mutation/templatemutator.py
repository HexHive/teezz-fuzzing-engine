import struct
import random
import re
import logging
from fuzz.seed.seedtemplate import SeedTemplate
from typing import List, Optional


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class TemplateMutatorException(Exception):
    pass


class TemplateMutator:
    NUMERIC_TYPES: List[str] = []
    NUMERIC_TYPES.extend(
        ["char", "signed char", "unsigned char", "int8_t", "uint8_t"]
    )
    NUMERIC_TYPES.extend(
        [
            "short",
            "short int",
            "signed short",
            "signed short int",
            "int16_t",
            "uint16_t",
        ]
    )
    NUMERIC_TYPES.extend(
        [
            "int",
            "signed",
            "signed int",
            "unsigned",
            "unsigned int",
            "int32_t",
            "uint32_t",
        ]
    )
    NUMERIC_TYPES.extend(
        [
            "long",
            "long int",
            "signed long",
            "unsigned long",
            "signed long int",
            "unsigned long int",
            "int64_t",
            "uint64_t",
        ]
    )
    NUMERIC_TYPES.extend(["off_t", "size_t"])

    BYTE_TYPES = ["char*", "unsigned char*", "uint8_t*", "int8_t*"]

    def __init__(self, proto_module):
        import importlib

        self._proto = importlib.import_module(proto_module)
        self.fpack = {
            1: TemplateMutator._p8,
            2: TemplateMutator._p16,
            4: TemplateMutator._p32,
            8: TemplateMutator._p64,
        }

    def mutate(self, data: bytes, type: Optional[SeedTemplate] = None) -> bytes:
        """Mutate `data` and return the mutated data.
        If `type` is a `str`, try to apply type-aware mutations where the value
        of `type` describes the type.
        If `type` is a `SeedTemplate`, `data` is mutated according to the
        types in the `SeedTemplate`.
        """

        # TODO: remove after testing
        if type:
            assert isinstance(type, SeedTemplate), f"{type} not SeedTemplate"

        if not type:
            # apply bit flips if we don't have a type
            data = TemplateMutator._flip_random_bit(data)
        else:
            data = self._mutate_complex(data, type)
        return data

    @staticmethod
    def _p8(v: int) -> bytes:
        return struct.pack("<B", v & 0xFF)

    @staticmethod
    def _p16(v: int) -> bytes:
        return struct.pack("<H", v & 0xFFFF)

    @staticmethod
    def _p32(v: int) -> bytes:
        return struct.pack("<I", v & 0xFFFFFFFF)

    @staticmethod
    def _p64(v: int) -> bytes:
        return struct.pack("<Q", v & 0xFFFFFFFFFFFFFFFF)

    def _mangle_type_name(self, type_name: str) -> str:
        # TODO implement actual mangling
        type_name = type_name.replace("const ", "", 1)
        type_name = type_name.replace("struct ", "", 1)
        type_name = type_name.replace("::", "colon").replace("<", "brackleft")
        type_name = type_name.replace(">", "brackright")
        type_name = type_name.replace(" ", "space").replace(",", "comma")
        return type_name

    def _normalize_type(self, type_name: str) -> str:
        type_name = type_name.replace("const ", "")
        tokens = [t for t in type_name.split(" ") if t]
        if tokens[-1] == "*":
            out_type_name = " ".join(tokens[:-1])
            out_type_name += tokens[-1]
        else:
            out_type_name = " ".join(tokens)
        return out_type_name

    def _mutate_complex(self, data: bytes, types: SeedTemplate) -> bytes:
        # get first param's data and types
        types = {e.start: (e.size, e.type) for e in types.listify()}
        type_keys = list(types.keys())

        # TODO: pre-compute this and add to `SeedTemplate`
        untyped_chunks = []
        off = 0
        for k, v in types.items():
            if off < k:
                untyped_chunks.append((off, k))
            off = k + v[0]

        # we mutate at least 1 and up to `len(type_keys)` typed fields of `data`
        ntypes = min(len(type_keys), 1 << random.randint(0, 5))
        nnotypes = min(len(untyped_chunks), 1 << random.randint(0, 5))
        # log.info(f"Mutating {ntypes} typed fields of current `param`")

        for _ in range(0, ntypes):
            type_idx = random.choice(type_keys)
            sz = types[type_idx][0]
            type_ = types[type_idx][1]
            updated = self._mutate_field(data[type_idx : type_idx + sz], type_)
            data = data[:type_idx] + updated + data[type_idx + sz :]

        for _ in range(0, nnotypes):
            start, end = random.choice(untyped_chunks)
            data = (
                data[:start]
                + TemplateMutator._flip_random_bit(data[start:end])
                + data[end:]
            )

        return data

    @staticmethod
    def _flip_random_bit(data: bytes) -> bytes:
        target_byte = random.randint(0, len(data) - 1)
        data_low = data[:target_byte]
        b = struct.pack("<B", data[target_byte] ^ (0x1 << random.randint(0, 7)))
        data_high = data[target_byte + 1 :]
        out = data_low + b + data_high
        assert len(data) == len(out)
        return out

    def _mutate_field(self, data: bytes, type_: str):
        size = len(data)
        mangled_type = self._mangle_type_name(type_)
        type_name = self._normalize_type(type_)

        if mangled_type in self._proto.DESCRIPTOR.enum_types_by_name:
            log.info(f"Type: {type_}")
            # handle TA-specific enum
            enum_desc = self._proto.DESCRIPTOR.enum_types_by_name[mangled_type]
            vals = [v for v in enum_desc.values]
            val = random.choice(vals)
            data = self.fpack[size](val.number)
        elif type_name in self.NUMERIC_TYPES:
            # handle numeric types
            # log.info("Mutating {}".format(type_))
            if len(data) == 1:
                char_magic_vals = [
                    0x0,
                    0x7F,
                    0x80,
                    0xFF,
                    random.randint(0x1, 0xFE),
                ]
                data = self._p8(random.choice(char_magic_vals))
            elif len(data) == 2:
                short_magic_vals = [
                    0x0,
                    0x7FFF,
                    0x8000,
                    0xFFFF,
                    random.randint(0x1, 0xFFFE),
                ]
                data = self._p16(random.choice(short_magic_vals))
            elif len(data) == 4:
                int_magic_vals = [
                    0x0,
                    0x7FFFFFFF,
                    0x80000000,
                    0xFFFFFFFF,
                    random.randint(0x1, 0xFFFFFFFE),
                ]
                data = self._p32(random.choice(int_magic_vals))
            elif len(data) == 8:
                longlong_magic_vals = [
                    0x0,
                    0x7FFFFFFFFFFFFFFF,
                    0x8000000000000000,
                    0xFFFFFFFFFFFFFFFF,
                    random.randint(0x1, 0xFFFFFFFFFFFFFFFE),
                ]
                data = self._p64(random.choice(longlong_magic_vals))
            else:
                raise NotImplementedError("Implement me!")
        elif type_name == "bool":
            assert len(data) == 1, "Expected `bool` to be of sz=1"
            data = b"\x01" if data == b"\x00" else b"\x01"
        elif type_name in self.BYTE_TYPES or re.match(r".*\[\d+\]", type_name):
            # handle pointers to byte sequences
            # matches for array types (i.e., uint8_t[3])
            data = self._flip_random_bit(data)
        else:
            log.warn(f"Type `{type_name}` not found.")
            data = self._flip_random_bit(data)

        return data
