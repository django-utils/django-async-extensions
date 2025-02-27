from inspect import iscoroutinefunction

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.http.response import HttpResponse

from django_async_extensions.amiddleware.base import AsyncMiddlewareMixin
from django_async_extensions.amiddleware.gzip import AsyncGZipMiddleware
from django_async_extensions.amiddleware.http import AsyncConditionalGetMiddleware
from django_async_extensions.amiddleware.locale import AsyncLocaleMiddleware
from django_async_extensions.amiddleware.security import AsyncSecurityMiddleware


class TestMiddlewareMixin:
    middlewares = [
        AsyncGZipMiddleware,
        AsyncConditionalGetMiddleware,
        AsyncLocaleMiddleware,
        AsyncSecurityMiddleware,
    ]

    def test_repr(self):
        class GetResponse:
            async def __call__(self):
                return HttpResponse()

        async def get_response():
            return HttpResponse()

        assert (
            repr(AsyncMiddlewareMixin(GetResponse()))
            == "<AsyncMiddlewareMixin get_response=GetResponse>"
        )
        assert (
            repr(AsyncMiddlewareMixin(get_response))
            == "<AsyncMiddlewareMixin get_response="
            "TestMiddlewareMixin.test_repr.<locals>.get_response>"
        )

    def test_passing_explicit_none(self, subtests):
        msg = "get_response must be provided"
        for middleware in self.middlewares:
            with subtests.test(middleware=middleware):
                with pytest.raises(ValueError, match=msg):
                    middleware(None)

    def test_coroutine(self, subtests):
        async def async_get_response(request):
            return HttpResponse()

        def sync_get_response(request):
            return HttpResponse()

        for middleware in self.middlewares:
            with subtests.test(middleware=middleware.__qualname__):
                middleware_instance = middleware(async_get_response)
                assert iscoroutinefunction(middleware_instance)

                with pytest.raises(ImproperlyConfigured):
                    middleware(sync_get_response)
