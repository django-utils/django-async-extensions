from inspect import iscoroutinefunction

import pytest

from django.core.exceptions import ImproperlyConfigured
from django.http.response import HttpResponse

from django_async_extensions.middleware.base import AsyncMiddlewareMixin

req = HttpResponse()
resp = HttpResponse()
resp_for_get_response = HttpResponse()


async def async_get_response(request):
    return resp_for_get_response


class ResponseMiddleware(AsyncMiddlewareMixin):
    async def process_request(self, request):
        return req

    async def process_response(self, request, response):
        return resp


class RequestMiddleware(AsyncMiddlewareMixin):
    async def process_request(self, request):
        return resp


class TestMiddlewareMixin:
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

    def test_call_is_async(self):
        assert iscoroutinefunction(AsyncMiddlewareMixin.__call__)

    def test_middleware_raises_if_get_response_is_sync(self):
        def get_response():
            return HttpResponse()

        with pytest.raises(ImproperlyConfigured):
            AsyncMiddlewareMixin(get_response)

    async def test_middleware_get_response(self, client):
        middleware = AsyncMiddlewareMixin(async_get_response)
        assert await middleware(client) is resp_for_get_response

    async def test_middleware_process_request(self, client, mocker):
        spy = mocker.spy(RequestMiddleware, "process_request")

        middleware = RequestMiddleware(async_get_response)
        result = await middleware(client)
        assert result is resp is spy.spy_return
        assert result is not resp_for_get_response
        assert spy.call_count == 1
        spy.assert_called_once_with(middleware, client)

    async def test_middleware_process_response(self, client, mocker):
        spy1 = mocker.spy(ResponseMiddleware, "process_request")
        spy2 = mocker.spy(ResponseMiddleware, "process_response")

        middleware = ResponseMiddleware(async_get_response)
        result = await middleware(client)

        assert result is resp is spy2.spy_return
        assert result is not resp_for_get_response
        assert spy2.call_count == 1
        spy2.assert_called_once_with(middleware, client, req)

        assert spy1.call_count == 1
        assert spy1.spy_return == req
