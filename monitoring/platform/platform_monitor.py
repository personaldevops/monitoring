from prometheus_client import CollectorRegistry, Gauge, Counter, Histogram, Summary, push_to_gateway
from typing import Dict, Union
from monitoring.platform import CustomTimer, CustomInprogressTracker


class MetricAlreadyExists(Exception):
 pass


class MethodNotAvailable(Exception):
 pass


class PlatformMonitor:
    def __init__(self, job_name: str):
        self.job_name = job_name
        self.collectors: Dict[str, Union[Gauge, Summary, Histogram, Counter]] = {}
        self.registry = CollectorRegistry()
        self.host_url = 'localhost:9091'

    def add_gauge(self, name: str, description: str, labels: list):
        if name in self.collectors.keys():
            raise MetricAlreadyExists(f'{name} already exists in the registry as a {type(self.collectors[name])}')
        self.collectors[name]: Gauge = Gauge(name=name, documentation=description, labelnames=labels)
        self.registry.register(self.collectors[name])

    def add_counter(self, name: str, description: str, labels: list):
        if name in self.collectors.keys():
            raise MetricAlreadyExists(f'{name} already exists in the registry as a {type(self.collectors[name])}')
        self.collectors[name]: Counter = Counter(name=name, documentation=description, labelnames=labels)
        self.registry.register(self.collectors[name])

    def add_summary(self, name: str, description: str, labels: list):
        if name in self.collectors.keys():
            raise MetricAlreadyExists(f'{name} already exists in the registry as a {type(self.collectors[name])}')
        self.collectors[name]: Summary = Summary(name=name, documentation=description, labelnames=labels)
        self.registry.register(self.collectors[name])

    def add_histogram(self, name: str, description: str, labels: list):
        if name in self.collectors.keys():
            raise MetricAlreadyExists(f'{name} already exists in the registry as a {type(self.collectors[name])}')
        self.collectors[name]: Histogram = Histogram(name=name, documentation=description, labelnames=labels)
        self.registry.register(self.collectors[name])

    def increment(self, name, labels):
        if hasattr(self.collectors[name], "inc"):
            self.collectors[name].labels(*labels).inc()
            self._push_metrics()
            return
        raise MethodNotAvailable(f'{type(self.collectors[name])} does not have increment operation')

    def decrement(self, name, labels):
        if hasattr(self.collectors[name], "dec"):
            self.collectors[name].labels(*labels).dec()
            self._push_metrics()
            return
        raise MethodNotAvailable(f'{type(self.collectors[name])} does not have decrement operation')

    def time(self, name, labels):
        if hasattr(self.collectors[name], "time"):
          return CustomTimer(metric=self.collectors[name], callback_name='set', url=self.host_url,registry=self.registry, labels=labels, job=self.job_name)
        raise MethodNotAvailable(f'{type(self.collectors[name])} does not have timer operation')

    def track_inprogress(self, name, labels):
        if hasattr(self.collectors[name], "track_inprogress"):
            return CustomInprogressTracker(gauge=self.collectors[name], url=self.host_url, registry=self.registry,job=self.job_name, labels=labels)
        raise MethodNotAvailable(f'{type(self.collectors[name])} does not have progress tracker operation')

    def set(self, name, labels, value):
        if hasattr(self.collectors[name], "set"):
            self.collectors[name].labels(*labels).set(value=value)
            self._push_metrics()
            return
        raise MethodNotAvailable(f'{type(self.collectors[name])} does not have set operation')

    def _push_metrics(self):
        push_to_gateway(gateway=self.host_url, job=self.job_name, registry=self.registry)