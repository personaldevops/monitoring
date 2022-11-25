from aioprometheus import Summary, Gauge
import time
from decorator import FunctionMaker

EXCLUDE_PATHS = (
    "/metrics",
    "/metrics/",
    "/docs",
    "/openapi.json",
    "/docs/oauth2-redirect",
    "/redoc",
    "/favicon.ico",
)

default_timer = time.perf_counter


def decorate(func, caller):
    """
    decorate(func, caller) decorates a function using a caller.
    """
    evaldict = dict(_call_=caller, _func_=func)
    fun = FunctionMaker.create(
        func, "return _call_(_func_, %(shortsignature)s)",
        evaldict, __wrapped__=func)
    if hasattr(func, '__qualname__'):
        fun.__qualname__ = func.__qualname__
    return fun


class Timer:
    def __init__(self, metric, callback_name, label):
        self._metric = metric
        self._callback_name = callback_name
        self.label = label

    def _new_timer(self):
        return self.__class__(self._metric, self._callback_name)

    def __enter__(self):
        self._start = default_timer()
        return self

    def __exit__(self, typ, value, traceback):
        # Time can go backwards.
        duration = max(default_timer() - self._start, 0)
        print(f'Prometheus time ---- {duration}')
        callback = getattr(self._metric, self._callback_name)
        callback(labels=self.label, value=duration)

    def __call__(self, f):
        def wrapped(func, *args, **kwargs):
            # Obtaining new instance of timer every time
            # ensures thread safety and reentrancy.
            with self._new_timer():
                return func(*args, **kwargs)

        return decorate(f, wrapped)


class InprogressTracker:
    def __init__(self, gauge: Gauge, labels):
        self._gauge = gauge
        self.labels = labels

    def __enter__(self):
        self._gauge.inc(labels=self.labels)

    def __exit__(self, typ, value, traceback):
        self._gauge.dec(labels=self.labels)

    def __call__(self, f):
        def wrapped(func, *args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return decorate(f, wrapped)


class CustomSummary(Summary):
    def __init__(self, name: str, doc: str, const_labels, registry):
        super(CustomSummary, self).__init__(name, doc, const_labels, registry)

    def time(self, label):
        time = Timer(self, 'add', label=label)
        return time


class CustomGauge(Gauge):
    def __init__(self, name: str, doc: str, const_labels, registry):
        super(CustomGauge, self).__init__(name, doc, const_labels, registry)

    def track_inprogress(self, labels) -> InprogressTracker:
        return InprogressTracker(self, labels=labels)