from aioprometheus import REGISTRY, Counter, Registry
from aioprometheus.mypy_types import LabelsType
from typing import Any, Awaitable, Callable, Dict, Sequence
from . import CustomSummary, CustomGauge, EXCLUDE_PATHS

Scope = Dict[str, Any]
Message = Dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGICallable = Callable[[Scope, Receive, Send], Awaitable[None]]


class MonitoringMiddleware:
    def __init__(self, app: ASGICallable, registry: Registry = REGISTRY, exclude_paths: Sequence[str] = EXCLUDE_PATHS,
                 use_template_urls: bool = True,
                 group_status_codes: bool = False,
                 const_labels: LabelsType = None,
                 ) -> None:
        self.asgi_callable = app

        self.starlette_app = None

        self.exclude_paths = exclude_paths if exclude_paths else []
        self.use_template_urls = use_template_urls
        self.group_status_codes = group_status_codes

        if registry is not None and not isinstance(registry, Registry):
            raise Exception(f"registry must be a Registry, got: {type(registry)}")
        self.registry = registry

        self.const_labels = const_labels

        self.metrics_created = False

    def create_metrics(self):
        """Create middleware metrics"""

        self.requests_counter = (  # pylint: disable=attribute-defined-outside-init
            Counter(
                "requests_total_counter",
                "Total number of requests received",
                const_labels=self.const_labels,
                registry=self.registry,
            )
        )
        self.req_time = (  # pylint: disable=attribute-defined-outside-init
            CustomSummary(
                "req_time",
                "Time taken to execute a request",
                const_labels=self.const_labels,
                registry=self.registry,
            )
        )
        self.in_progress = (  # pylint: disable=attribute-defined-outside-init
            CustomGauge(
                "in_progress",
                "Total number of requests in_progress",
                const_labels=self.const_labels,
                registry=self.registry,
            )
        )
        self.responses_counter = (  # pylint: disable=attribute-defined-outside-init
            Counter(
                "responses_total_counter",
                "Total number of responses sent",
                const_labels=self.const_labels,
                registry=self.registry,
            )
        )

        self.exceptions_counter = (  # pylint: disable=attribute-defined-outside-init
            Counter(
                "exceptions_total_counter",
                "Total number of requested which generated an exception",
                const_labels=self.const_labels,
                registry=self.registry,
            )
        )

        self.status_codes_counter = (  # pylint: disable=attribute-defined-outside-init
            Counter(
                "status_codes_counter",
                "Total number of response status codes",
                const_labels=self.const_labels,
                registry=self.registry,
            )
        )

        self.metrics_created = True

    async def call(self, scope, receive, send):
        await self.asgi_callable(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):

        if not self.metrics_created:
            self.create_metrics()

        if scope["type"] == "lifespan":
            self.starlette_app = scope.get("app")
        if scope["type"] != "http":
            await self.call(scope, receive, send)
            return

        def wrapped_send(response):

            if response["type"] == "http.response.start":
                status_code_labels = labels.copy()
                status_code = str(response["status"])
                status_code_labels["status_code"] = (
                    f"{status_code[0]}xx" if self.group_status_codes else status_code
                )
                self.status_codes_counter.inc(status_code_labels)
                self.responses_counter.inc(labels)

            return send(response)

        method = scope["method"]
        path = self.get_full_or_template_path(scope)

        if path in self.exclude_paths:
            await self.call(scope, receive, send)
            return

        labels = dict(method=method, path=path)

        self.requests_counter.inc(labels)
        try:
            with self.req_time.time(label=labels):
                with self.in_progress.track_inprogress(labels=labels):
                    await self.call(scope, receive, wrapped_send)
        except Exception:
            self.exceptions_counter.inc(labels)

            status_code_labels = labels.copy()
            status_code_labels["status_code"] = (
                "5xx" if self.group_status_codes else "500"
            )
            self.status_codes_counter.inc(status_code_labels)
            self.responses_counter.inc(labels)

            raise

    def get_full_or_template_path(self, scope) -> str:

        root_path = scope.get("root_path", "")
        path = scope.get("path", "")
        full_path = f"{root_path}{path}"

        if self.use_template_urls:
            if self.starlette_app:

                for route in self.starlette_app.routes:
                    match, _child_scope = route.matches(scope)

                    if match.value == 2:
                        return route.path

        return full_path
