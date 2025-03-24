import logging

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, HttpResponseNotAllowed

from django.utils.decorators import classonlymethod
from django.utils.functional import classproperty
from django.views.generic.base import (
    View,
    TemplateResponseMixin,
    RedirectView,
)

logger = logging.getLogger("django.request")


class AsyncContextMixin:
    """
    A default context mixin that passes the keyword arguments received by
    get_context_data() as the template context.
    """

    extra_context = None

    async def get_context_data(self, **kwargs):
        kwargs.setdefault("view", self)
        if self.extra_context is not None:
            kwargs.update(self.extra_context)
        return kwargs


class AsyncView(View):
    @classproperty
    def view_is_async(cls):
        handlers = [
            getattr(cls, method)
            for method in cls.http_method_names
            if (method != "options" and hasattr(cls, method))
        ]
        if not handlers:
            return False
        is_async = iscoroutinefunction(handlers[0])
        if not all(iscoroutinefunction(h) == is_async for h in handlers[1:]):
            raise ImproperlyConfigured(
                f"{cls.__qualname__} HTTP handlers must all be async."
            )
        return is_async

    @classonlymethod
    def as_view(cls, **initkwargs):
        """Main entry point for a request-response process."""
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError(
                    f"The method name {key} is not accepted as a keyword argument "
                    f"to {cls.__name__}()."
                )
            if not hasattr(cls, key):
                raise TypeError(
                    f"{cls.__name__}() received an invalid keyword '{key}'. as_view "
                    f"only accepts arguments that are already "
                    f"attributes of the class."
                )

        async def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            self.setup(request, *args, **kwargs)
            if not hasattr(self, "request"):
                raise AttributeError(
                    f"{cls.__name__} instance has no 'request' attribute. "
                    f"Did you override setup() and forgot to call super()?"
                )
            return await self.dispatch(request, *args, **kwargs)

        view.view_class = cls
        view.view_initkwargs = initkwargs

        # __name__ and __qualname__ are intentionally left unchanged as
        # view_class should be used to robustly determine the name of the view
        # instead.
        view.__doc__ = cls.__doc__
        view.__module__ = cls.__module__
        view.__annotations__ = cls.dispatch.__annotations__
        # Copy possible attributes set by decorators, e.g. @csrf_exempt, from
        # the dispatch method.
        view.__dict__.update(cls.dispatch.__dict__)

        # Mark the callback if the view class is async.
        markcoroutinefunction(view)

        return view

    async def dispatch(self, request, *args, **kwargs):
        # Try to dispatch to the right method; if a method doesn't exist,
        # defer to the error handler. Also defer to the error handler if the
        # request method isn't on the approved list.
        if request.method.lower() in self.http_method_names:
            handler = getattr(
                self, request.method.lower(), self.http_method_not_allowed
            )
        else:
            handler = self.http_method_not_allowed
        return await handler(request, *args, **kwargs)

    async def http_method_not_allowed(self, request, *args, **kwargs):
        logger.warning(
            "Method Not Allowed (%s): %s",
            request.method,
            request.path,
            extra={"status_code": 405, "request": request},
        )
        response = HttpResponseNotAllowed(self._allowed_methods())

        return response

    async def options(self, request, *args, **kwargs):
        """Handle responding to requests for the OPTIONS HTTP verb."""
        response = HttpResponse()
        response.headers["Allow"] = ", ".join(self._allowed_methods())
        response.headers["Content-Length"] = "0"

        return response


class AsyncTemplateResponseMixin(TemplateResponseMixin):
    async def render_to_response(self, context, **response_kwargs):
        """
        Return a response, using the `response_class` for this view, with a
        template rendered with the given context.

        Pass response_kwargs to the constructor of the response class.
        """
        response_kwargs.setdefault("content_type", self.content_type)
        return await sync_to_async(self.response_class)(
            request=self.request,
            template=self.get_template_names(),
            context=context,
            using=self.template_engine,
            **response_kwargs,
        )


class AsyncTemplateView(AsyncTemplateResponseMixin, AsyncContextMixin, AsyncView):
    """
    Render a template. Pass keyword arguments from the URLconf to the context.
    """

    async def get(self, request, *args, **kwargs):
        context = await self.get_context_data(**kwargs)
        return await self.render_to_response(context)


class AsyncRedirectView(AsyncView, RedirectView):
    """Provide a redirect on any GET request."""

    async def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    async def head(self, request, *args, **kwargs):
        return await self.get(request, *args, **kwargs)

    async def post(self, request, *args, **kwargs):
        return await self.get(request, *args, **kwargs)

    async def options(self, request, *args, **kwargs):
        return await self.get(request, *args, **kwargs)

    async def delete(self, request, *args, **kwargs):
        return await self.get(request, *args, **kwargs)

    async def put(self, request, *args, **kwargs):
        return await self.get(request, *args, **kwargs)

    async def patch(self, request, *args, **kwargs):
        return await self.get(request, *args, **kwargs)
