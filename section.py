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

class Metric:
    def __init__(self, label, name, value, unit):
        self._label = label
        self._name = name
        self._value = value
        self._unit = unit

    def label(self):
        return self._label

    def name(self):
        return self._name

    def value(self):
        return self._value

    def unit(self):
        return self._unit


class Section:
    def __init__(self, name):
        self.name = name
        self.metrics = []

    def add_entry(self, metric):
        if self.name:
            self.metrics.append(metric)

    def get_entries(self):
        return self.metrics

    def count(self):
        return len(self.metrics)

    def __getitem__(self, key):
        if key < 0 or key >= len(self.metrics):
            return None
        m = self.metrics[key] 
        return {
            'metric_label': m.label(),
            'metric_name': m.name(),
            'metric_value': m.value(),
            'metric_unit': m.unit()
        }

    def __str__(self):
        s = f'section : {self.name}\n'
        for i in range(len(self.metrics)):
            m = self.metrics[i]
            s += f'    {m.label()} => {m.name()}\n'
        return s

    def __add__(self, other):
        if not isinstance(other, Section):
            return NotImplemented

        new_section = Section(f"{self.name} + {other.name}")
        metrics_map = {}

        def merge_metrics(metrics_list):
            for m in metrics_list:
                name = m.name()
                if name in metrics_map:
                    current_val = metrics_map[name][1]
                    new_val = m.value()

                    if isinstance(current_val, str) or isinstance(new_val, str):
                        metrics_map[name][1] = current_val
                    else:
                        metrics_map[name][1] += new_val
                else:
                    metrics_map[name] = [m.label(), m.value(), m.unit()]

        merge_metrics(self.metrics)
        merge_metrics(other.metrics)

        for name, data in metrics_map.items():
            new_metric = Metric(
                label=data[0],
                name=name,
                value=data[1],
                unit=data[2]
            )
            new_section.add_entry(new_metric)

        return new_section

    def __truediv__(self, divisor):
        if not isinstance(divisor, (int, float)):
            return NotImplemented

        if divisor == 1:
            return self

        new_section = Section(self.name)
        for m in self.metrics:
            val = m.value()
            final_value = val if isinstance(val, str) else val / divisor

            new_metric = Metric(
                label=m.label(),
                name=m.name(),
                value=final_value,
                unit=m.unit()
            )
            new_section.add_entry(new_metric)
        return new_section
