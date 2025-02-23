from django.conf import settings
from django.http import Http404
from django.utils.deprecation import MiddlewareMixin

from asgiref.sync import sync_to_async

from django_async_extensions.acontrib.flatpages.views import flatpage


class AsyncFlatpageFallbackMiddleware(MiddlewareMixin):
    async def process_response(self, request, response):
        if response.status_code != 404:
            return response  # No need to check for a flatpage for non-404 responses.
        try:
            return await flatpage(request, request.path_info)
        # Return the original response if any errors happened. Because this
        # is a middleware, we can't assume the errors will be caught elsewhere.
        except Http404:
            return response
        except Exception:
            if settings.DEBUG:
                raise
            return response

    async def __acall__(self, request):
        """
        Async version of __call__ that is swapped in when an async request
        is running.
        """
        response = None
        if hasattr(self, "process_request"):
            response = await sync_to_async(
                self.process_request,
                thread_sensitive=True,
            )(request)
        response = response or await self.get_response(request)
        if hasattr(self, "process_response"):
            response = await self.process_response(request, response)
        return response
