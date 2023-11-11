from __future__ import annotations
from dataclasses import dataclass

from typing import List, Optional

import logging


logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


@dataclass
class SeedTemplateElement:
    start: int
    end: int
    type: str

    @property
    def size(self) -> int:
        """Returns the size of this element.

        Returns:
            int: size of this element.
        """
        return self.end - self.start

    def is_collision(self, elem: SeedTemplateElement):
        if self.start > elem.start and self.end >= elem.end:
            return False
        elif self.end <= elem.start and self.end < elem.end:
            return False
        else:
            log.debug(f"Collision detected: {self} collides with {elem}")
            return True


class SeedTemplate:
    def __init__(
        self,
        total_size: int,
        init_list: Optional(List[SeedTemplateElement]) = None,
    ):
        self._elements = dict()
        self._size = total_size

        if init_list:
            for elem in init_list:
                self.add_elem(elem)

    @property
    def size(self):
        return self._size

    def add_elems(self, elems: List[SeedTemplateElement]):
        for elem in elems:
            self.add_elem(elem)

    def add_elem(self, new_elem: SeedTemplateElement):
        if new_elem.start >= self._size or new_elem.end > self._size:
            import ipdb

            ipdb.set_trace()

        # go through all the types and check if we have a collision
        for elem in self._elements.values():
            if elem.is_collision(new_elem):
                raise ValueError("Already existing range with different type!")
        self._elements[new_elem.start] = new_elem

    def listify(self):
        # return list of values sorted by key
        return [self._elements[k] for k in sorted(self._elements.keys())]

    def __str__(self):
        out = ""
        for elem in self._elements.values():
            out += f"{elem}\n"
        return out
