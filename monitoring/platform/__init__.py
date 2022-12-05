from timeit import default_timer
from prometheus_client.decorator import decorate

from prometheus_client import push_to_gateway


class CustomInprogressTracker:
     def __init__(self, gauge, url, registry, job, labels):
         self._gauge = gauge
         self.url = url
         self.job = job
         self.registry = registry
         self._gauge.labels(*labels)

     def __enter__(self):
         self._gauge.inc()
         push_to_gateway(gateway=self.url, job=self.job, registry=self.registry)

     def __exit__(self, typ, value, traceback):
         self._gauge.dec()
         push_to_gateway(gateway=self.url, job=self.job, registry=self.registry)

     def __call__(self, f):
         def wrapped(func, *args, **kwargs):
             with self:
                return func(*args, **kwargs)

         return decorate(f, wrapped)


class CustomTimer:
    def __init__(self, metric, callback_name, url, registry, job, labels):
         self._metric = metric
         self._callback_name = callback_name
         self.url = url
         self.job = job
         self.registry = registry
         self._metric.labels(*labels)

    def _new_timer(self):
        return self.__class__(self._metric, self._callback_name)

    def __enter__(self):
        self._start = default_timer()
        return self

    def __exit__(self, typ, value, traceback):
         duration = max(default_timer() - self._start, 0)
         callback = getattr(self._metric, self._callback_name)
         callback(duration)
         push_to_gateway(gateway=self.url, job=self.job, registry=self.registry)

    def __call__(self, f):
        def wrapped(func, *args, **kwargs):
     # Obtaining new instance of timer every time
     # ensures thread safety and reentrancy.
            with self._new_timer():
                return func(*args, **kwargs)

        return decorate(f, wrapped)