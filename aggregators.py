# easy-ncu - A smart CLI tool for NVIDIA Nsight Compute report analysis.
# Copyright (C) 2026  Salvatore Biamonte
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from abc import ABC, abstractmethod
from collections import defaultdict
import section


class Aggregator(ABC):
    def __init__(self, irange, start, count, should_load=True):
        import __main__ as main_module
        self.main_mod = main_module

        self.irange = irange
        self.start = start
        self.count = count
        self.has_changed_slice = False
        self.sections = []
        self.cached = None
        if should_load:
            self._load_all()

    def set_slice(self, start, count):
        self.start = start
        self.count = count
        self.has_changed_slice = True
        self.cached = None

    def load(self):
        self._load_all()

    def _load_all(self):
        self.sections = []
        for i in range(self.start, self.start + self.count):
            action = self.irange.action_by_idx(i)
            self.sections.append(self.main_mod.load_sections(action))

    @abstractmethod
    def aggregate(self):
        pass


class SumAggregator(Aggregator):
    def aggregate(self):
        if self.cached and not self.has_changed_slice:
            return self.cached

        if self.sections:
            aggregated = defaultdict(lambda: None)
            for sect_dict in self.sections:
                for key, obj in sect_dict.items():
                    if aggregated[key] is None:
                        initial_section = section.Section(key)
                        for metric in obj.get_entries():
                            cloned_metric = section.Metric(
                                label=metric.label(),
                                name=metric.name(),
                                value=metric.value(),
                                unit=metric.unit()
                            )
                            initial_section.add_entry(cloned_metric)
                        aggregated[key] = initial_section
                    else:
                        aggregated[key] = aggregated[key] + obj
            self.cached = dict(aggregated)
            return self.cached
        return None


class AvgAggregator(SumAggregator):
    def aggregate(self):
        if self.cached and not self.has_changed_slice:
            return self.cached

        summed_dict = super().aggregate()
        if not summed_dict:
            return None

        total_elements = len(self.sections)
        averaged_dict = {}
        for key, obj in summed_dict.items():
            averaged_dict[key] = obj / total_elements

        self.cached = averaged_dict
        self.has_changed_slice = False
        return self.cached
