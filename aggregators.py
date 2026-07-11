from abc import ABC, abstractclassmethod, abstractmethod
from collections import defaultdict
import section


class Aggregator(ABC):
    SECTIONS = [
        'GPU Speed Of Light Throughput',
        'Compute Workload Analysis',
        'Warp State Statistics',
        'Occupancy'
    ]

    def __init__(self, irange, start, count):
        import __main__ as main_module
        self.main_mod = main_module

        self.irange = irange
        self.start = start
        self.count = count
        self.sections = []
        self.cached = None
        self._load_all()

    def _load_all(self):
        for i in range(self.start, self.start+self.count):
            action = self.irange.action_by_idx(i)
            self.sections.append(self.main_mod.load_sections(action))

    @abstractmethod
    def aggregate(self):
        pass


class SumAggregator(Aggregator):
    def aggregate(self):
        if self.cached:
            return self.cached

        if self.sections:
            aggregated = defaultdict(lambda: None)
            for sect_dict in self.sections:
                for key, obj in sect_dict.items():
                    if aggregated[key] is None:
                        initial_section = section.Section(key)
                        for metric in obj.get_entries():
                            initial_section.add_entry(metric)
                        aggregated[key] = initial_section
                    else:
                        aggregated[key] = aggregated[key] + obj
            self.cached = dict(aggregated)
            return self.cached
        return None


