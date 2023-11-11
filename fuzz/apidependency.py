from __future__ import annotations
import logging
import os
from collections import UserList
from typing import List, Optional

log = logging.getLogger(__name__)


class DumpIdCollisionException(Exception):
    pass


class IoctlCallSequence(list):
    """A sequence_id ordered structure of IoctlCall objects."""

    def __init__(self, *args):
        list.__init__(self, *args)
        self.dump_ids: List[int] = []

    def get_elem_by_dump_id(self, dump_id: int) -> Optional[IoctlCall]:
        for elem in self:
            if dump_id == elem.dump_id:
                return elem
        return None

    def append(self, item: IoctlCall):
        if not isinstance(item, IoctlCall):
            raise TypeError("item is not of type %s" % IoctlCall)
        if item.dump_id not in self.dump_ids:
            self.dump_ids.append(item.dump_id)
        super(IoctlCallSequence, self).append(item)

    def get_value_dependencies(self):
        """Get a list of all val deps in this seq."""
        l = []
        for ioctl in self:
            l.extend(ioctl.value_dependencies)
        return l

    def remove_value_dependency(self, vd: ValueDependency):
        """Find and remove value dependency `vd` from call seq. Returns `True`
        if `vd` was found and removed, `False` otherwise."""

        for ioctl in self:
            if vd in ioctl.value_dependencies:
                ioctl.value_dependencies.remove(vd)
                return True
        return False

    def __str__(self) -> str:
        out = ""
        for elem in self:
            out += elem.__str__()
            out += ", "
        return out


class IoctlCall:
    """An IoctlCall is a single call to a given ioctl API.
    It is part of an ioctl sequence.
    The call might have a value dependence to another call within its ioctl sequence.
    """

    def __init__(
        self,
        dump_group_id: int = None,
        dump_id: int = None,
        is_dump_backed: bool = True,
        **kwargs,
    ):
        self._is_dump_backed = is_dump_backed
        self._dump_group_id = dump_group_id
        self.dump_id = dump_id

        self.req = None  # implementation specific ingoing ioctl data
        self.resp = None  # implementation specific outgoing ioctl data
        self.value_dependencies = ValueDependencies()
        self.meta_info = (
            kwargs  # e.g., which HAL function this call corresponds to
        )

    def __str__(self):
        out = ""
        out += "IoctlCall({:#x}) {{\n".format(self.dump_id)
        for val_dep in self.value_dependencies:
            out += "\t{}".format(val_dep)
        out += "}"
        return out

    @property
    def relative_path(self):
        if self._is_dump_backed:
            return os.path.join(str(self._dump_group_id), str(self.dump_id))
        else:
            return None


class ValueDependencies(UserList):

    def append(self, new_vd: ValueDependency):
        if not self.data:
            self.data.append(new_vd)
            return

        for vd in self.data:
            if new_vd.dst_id == vd.dst_id and ValueDependencies.is_overlap(
                new_vd, vd
            ):
                # we already have a depencency for this destination
                # and the two deps are overlapping
                if new_vd.dst_sz > vd.dst_sz:
                    # be greedy and replace if smaller
                    self.data[self.data.index(vd)] = new_vd
                return
        self.data.append(new_vd)

    @staticmethod
    def is_overlap(vd1: ValueDependency, vd2: ValueDependency) -> bool:
        start1 = vd1.dst_off
        start2 = vd2.dst_off
        end1 = vd1.dst_off + vd1.dst_sz
        end2 = vd2.dst_off + vd2.dst_sz

        # start of vd1 is in range of vd2
        if start1 >= start2 and start1 < end2:
            return True
        # end of vd1 is in range of vd2
        if end1 > start2 and end1 <= end2:
            return True
        # vd1 contains vd2
        if start1 < start2 and end1 > end2:
            return True
        return False


class ValueDependency:
    """A ValueDependency expresses a data dependency of an IoctlCall to a
    preceeding IoctlCall. I.e., if a preceeding ioctl's response provides data
    that is consumed by the ioctl this value dependency belongs to.
    """

    def __init__(
        self,
        src_ioctl_call: IoctlCall,
        src_id: str,
        src_off: int,
        src_sz: int,
        dst_id: str,
        dst_off: int,
        dst_sz: int,
    ):
        self.src_ioctl_call = src_ioctl_call

        # target specific identifier (i.e, param_0_a for tc or resp for qsee)
        self.src_id = src_id
        self.src_off = src_off
        self.src_sz = src_sz
        self.dst_id = dst_id
        self.dst_off = dst_off
        self.dst_sz = dst_sz

    def __str__(self):
        out = f"src=IoctlCall({self.src_ioctl_call.dump_id:#x}) "
        out += f"({self.src_id}, off={self.src_off}, sz={self.src_sz})"
        out += f" --> "
        out += f"({self.dst_id}, off={self.dst_off}, sz={self.dst_sz})\n"
        return out
