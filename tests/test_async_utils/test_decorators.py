from asgiref.sync import sync_to_async

import pytest

from django.http import HttpResponse
from django.template import engines
from django.template.response import TemplateResponse
from django.test import RequestFactory

from django_async_extensions.middleware.base import AsyncMiddlewareMixin
from django_async_extensions.utils.decorators import decorator_from_middleware


class ProcessViewMiddleware(AsyncMiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    async def process_view(self, request, view_func, view_args, view_kwargs):
        pass


process_view_dec = decorator_from_middleware(ProcessViewMiddleware)


@process_view_dec
async def async_process_view(request):
    return HttpResponse()


@process_view_dec
def process_view(request):
    return HttpResponse()


class ClassProcessView:
    def __call__(self, request):
        return HttpResponse()


class_process_view = process_view_dec(ClassProcessView())


class AsyncClassProcessView:
    async def __call__(self, request):
        return HttpResponse()


async_class_process_view = process_view_dec(AsyncClassProcessView())


class FullMiddleware(AsyncMiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    async def process_request(self, request):
        request.process_request_reached = True

    async def process_view(self, request, view_func, view_args, view_kwargs):
        request.process_view_reached = True

    async def process_template_response(self, request, response):
        request.process_template_response_reached = True
        return response

    async def process_response(self, request, response):
        # This should never receive unrendered content.
        request.process_response_content = response.content
        request.process_response_reached = True
        return response


full_dec = decorator_from_middleware(FullMiddleware)


class TestDecoratorFromMiddleware:
    """
    Tests for view decorators created using
    ``django.utils.decorators.decorator_from_middleware``.
    """

    rf = RequestFactory()

    def test_process_view_middleware(self):
        """
        Test a middleware that implements process_view.
        """
        process_view(self.rf.get("/"))

    async def test_process_view_middleware_async(self, async_rf):
        await async_process_view(async_rf.get("/"))

    async def test_sync_process_view_raises_in_async_context(self):
        msg = (
            "You cannot use AsyncToSync in the same thread as an async event loop"
            " - just await the async function directly."
        )
        with pytest.raises(RuntimeError, match=msg):
            process_view(self.rf.get("/"))

    def test_callable_process_view_middleware(self):
        """
        Test a middleware that implements process_view, operating on a callable class.
        """
        class_process_view(self.rf.get("/"))

    async def test_callable_process_view_middleware_async(self, async_rf):
        await async_process_view(async_rf.get("/"))

    def test_full_dec_normal(self):
        """
        All methods of middleware are called for normal HttpResponses
        """

        @full_dec
        def normal_view(request):
            template = engines["django"].from_string("Hello world")
            return HttpResponse(template.render())

        request = self.rf.get("/")
        normal_view(request)
        assert getattr(request, "process_request_reached", False)
        assert getattr(request, "process_view_reached", False)
        # process_template_response must not be called for HttpResponse
        assert getattr(request, "process_template_response_reached", False) is False
        assert getattr(request, "process_response_reached", False)

    async def test_full_dec_normal_async(self, async_rf):
        """
        All methods of middleware are called for normal HttpResponses
        """

        @full_dec
        async def normal_view(request):
            template = engines["django"].from_string("Hello world")
            return HttpResponse(template.render())

        request = async_rf.get("/")
        await normal_view(request)
        assert getattr(request, "process_request_reached", False)
        assert getattr(request, "process_view_reached", False)
        # process_template_response must not be called for HttpResponse
        assert getattr(request, "process_template_response_reached", False) is False
        assert getattr(request, "process_response_reached", False)

    def test_full_dec_templateresponse(self):
        """
        All methods of middleware are called for TemplateResponses in
        the right sequence.
        """

        @full_dec
        def template_response_view(request):
            template = engines["django"].from_string("Hello world")
            return TemplateResponse(request, template)

        request = self.rf.get("/")
        response = template_response_view(request)
        assert getattr(request, "process_request_reached", False)
        assert getattr(request, "process_view_reached", False)
        assert getattr(request, "process_template_response_reached", False)
        # response must not be rendered yet.
        assert response._is_rendered is False
        # process_response must not be called until after response is rendered,
        # otherwise some decorators like csrf_protect and gzip_page will not
        # work correctly. See #16004
        assert getattr(request, "process_response_reached", False) is False
        response.render()
        assert getattr(request, "process_response_reached", False)
        # process_response saw the rendered content
        assert request.process_response_content == b"Hello world"

    async def test_full_dec_templateresponse_async(self, async_rf):
        """
        All methods of middleware are called for TemplateResponses in
        the right sequence.
        """

        @full_dec
        async def template_response_view(request):
            template = engines["django"].from_string("Hello world")
            return TemplateResponse(request, template)

        request = async_rf.get("/")
        response = await template_response_view(request)
        assert getattr(request, "process_request_reached", False)
        assert getattr(request, "process_view_reached", False)
        assert getattr(request, "process_template_response_reached", False)
        # response must not be rendered yet.
        assert response._is_rendered is False
        # process_response must not be called until after response is rendered,
        # otherwise some decorators like csrf_protect and gzip_page will not
        # work correctly. See #16004
        assert getattr(request, "process_response_reached", False) is False
        await sync_to_async(response.render)()
        assert getattr(request, "process_response_reached", False)
        # process_response saw the rendered content
        assert request.process_response_content == b"Hello world"
