from asgiref.sync import iscoroutinefunction, markcoroutinefunction

from django.core.exceptions import ImproperlyConfigured


class AsyncMiddlewareMixin:
    sync_capable = False
    async_capable = True

    def __init__(self, get_response):
        if get_response is None:
            raise ValueError("get_response must be provided.")
        self.get_response = get_response
        # If get_response is not an async function, raise an error.
        self.async_mode = iscoroutinefunction(self.get_response) or iscoroutinefunction(
            getattr(self.get_response, "__call__", None)
        )
        if self.async_mode:
            # Mark the class as async-capable.
            markcoroutinefunction(self)
        else:
            raise ImproperlyConfigured("get_response must be async")

        super().__init__()

    def __repr__(self):
        return "<%s get_response=%s>" % (
            self.__class__.__qualname__,
            getattr(
                self.get_response,
                "__qualname__",
                self.get_response.__class__.__name__,
            ),
        )

    async def __call__(self, request):
        response = None
        if hasattr(self, "process_request"):
            response = await self.process_request(request)
        response = response or await self.get_response(request)
        if hasattr(self, "process_response"):
            response = await self.process_response(request, response)
        return response
