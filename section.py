

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
        if 0 > key > len(self.metrics)-1:
            return None
        m = self.metrics[key] 
        return {
            'metric_label' : m.label(),
            'metric_name' : m.name(),
            'metric_value' : m.value(),
            'metric_unit' : m.unit()
        }

    def __str__(self):
        s = f'section : {self.name}\n'
        for i in range(len(self.metrics)):
            m = self.metrics[i]
            s += f'    {m.label()} => {m.name()}\n'
        return s
