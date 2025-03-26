import logging

import pytest

from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpResponse
from django.test import override_settings

from . import middlewares as mw


class TestMiddleware:
    @pytest.fixture(autouse=True)
    def setup(self, settings):
        settings.ROOT_URLCONF = "test_middlewares.urls"
        yield
        mw.log = []

    def test_process_view_return_none(self, settings, client):
        settings.MIDDLEWARE = ["test_middlewares.middlewares.ProcessViewNoneMiddleware"]
        response = client.get("/middleware_exceptions/view/")
        assert mw.log == ["processed view normal_view"]
        assert response.content == b"OK"

    def test_process_view_return_response(self, settings, client):
        settings.MIDDLEWARE = ["test_middlewares.middlewares.ProcessViewMiddleware"]
        response = client.get("/middleware_exceptions/view/")
        assert response.content == b"Processed view normal_view"

    def test_templateresponse_from_process_view_rendered(self, settings, client):
        """
        TemplateResponses returned from process_view() must be rendered before
        being passed to any middleware that tries to access response.content,
        such as test_middlewares.middlewares.LogMiddleware.
        """
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.ProcessViewTemplateResponseMiddleware",
            "test_middlewares.middlewares.LogMiddleware",
        ]
        response = client.get("/middleware_exceptions/view/")
        assert (
            response.content
            == b"Processed view normal_view\nProcessViewTemplateResponseMiddleware"
        )

    def test_templateresponse_from_process_view_passed_to_process_template_response(
        self, settings, client
    ):
        """
        TemplateResponses returned from process_view() should be passed to any
        template response middleware.
        """
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.ProcessViewTemplateResponseMiddleware",
            "test_middlewares.middlewares.TemplateResponseMiddleware",
        ]
        response = client.get("/middleware_exceptions/view/")
        expected_lines = [
            b"Processed view normal_view",
            b"ProcessViewTemplateResponseMiddleware",
            b"TemplateResponseMiddleware",
        ]
        assert response.content == b"\n".join(expected_lines)

    def test_process_template_response(self, settings, client):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.TemplateResponseMiddleware"
        ]
        response = client.get("/middleware_exceptions/template_response/")
        assert response.content == b"template_response OK\nTemplateResponseMiddleware"

    def test_process_template_response_returns_none(self, settings, client):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.NoTemplateResponseMiddleware"
        ]
        msg = (
            "NoTemplateResponseMiddleware.process_template_response didn't "
            "return an HttpResponse object. It returned None instead."
        )
        with pytest.raises(ValueError, match=msg):
            client.get("/middleware_exceptions/template_response/")

    def test_view_exception_converted_before_middleware(self, settings, client):
        settings.MIDDLEWARE = ["test_middlewares.middlewares.LogMiddleware"]
        response = client.get("/middleware_exceptions/permission_denied/")
        assert mw.log == [(response.status_code, response.content)]
        assert response.status_code == 403

    def test_view_exception_handled_by_process_exception(self, settings, client):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.ProcessExceptionMiddleware"
        ]
        response = client.get("/middleware_exceptions/error/")
        assert response.content == b"Exception caught"

    def test_response_from_process_exception_short_circuits_remainder(
        self, settings, client
    ):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.ProcessExceptionLogMiddleware",
            "test_middlewares.middlewares.ProcessExceptionMiddleware",
        ]
        response = client.get("/middleware_exceptions/error/")
        assert mw.log == []
        assert response.content == b"Exception caught"

    def test_response_from_process_exception_when_return_response(
        self, settings, client
    ):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.ProcessExceptionMiddleware",
            "test_middlewares.middlewares.ProcessExceptionLogMiddleware",
        ]
        response = client.get("/middleware_exceptions/error/")
        assert mw.log == ["process-exception"]
        assert response.content == b"Exception caught"

    @override_settings(
        MIDDLEWARE=[
            "test_middlewares.middlewares.LogMiddleware",
            "test_middlewares.middlewares.NotFoundMiddleware",
        ]
    )
    def test_exception_in_middleware_converted_before_prior_middleware(
        self, settings, client
    ):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.LogMiddleware",
            "test_middlewares.middlewares.NotFoundMiddleware",
        ]
        response = client.get("/middleware_exceptions/view/")
        assert mw.log == [(404, response.content)]
        assert response.status_code == 404

    def test_exception_in_render_passed_to_process_exception(self, settings, client):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.ProcessExceptionMiddleware"
        ]
        response = client.get("/middleware_exceptions/exception_in_render/")
        assert response.content == b"Exception caught"


class TestRootUrlconf:
    @pytest.fixture(autouse=True)
    def setup(self, settings):
        settings.ROOT_URLCONF = "test_middlewares.urls"

    def test_missing_root_urlconf(self, settings, client):
        # Removing ROOT_URLCONF is safe, as override_settings will restore
        # the previously defined settings.
        del settings.ROOT_URLCONF
        with pytest.raises(AttributeError):
            client.get("/middleware_exceptions/view/")


class MyMiddleware:
    def __init__(self, get_response):
        raise MiddlewareNotUsed

    async def process_request(self, request):
        pass


class MyMiddlewareWithExceptionMessage:
    def __init__(self, get_response):
        raise MiddlewareNotUsed("spam eggs")

    async def process_request(self, request):
        pass


class TestMiddlewareNotUsed:
    @pytest.fixture(autouse=True)
    def setup(self, settings):
        settings.DEBUG = True
        settings.ROOT_URLCONF = "test_middlewares.urls"
        settings.MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]

    async def test_raise_exception(self, rf):
        request = rf.get("test_middlewares/view/")
        with pytest.raises(MiddlewareNotUsed):
            await MyMiddleware(lambda req: HttpResponse()).process_request(request)

    def test_log(self, settings, client, caplog):
        settings.MIDDLEWARE = ["test_middlewares.test_exceptions.MyMiddleware"]
        with caplog.at_level(logging.DEBUG, logger="django.request"):
            client.get("/middleware_exceptions/view/")
            assert (
                "MiddlewareNotUsed: 'test_middlewares.test_exceptions.MyMiddleware'"
                in caplog.text
            )

    def test_log_custom_message(self, settings, client, caplog):
        settings.MIDDLEWARE = [
            "test_middlewares.test_exceptions.MyMiddlewareWithExceptionMessage"
        ]
        with caplog.at_level(logging.DEBUG, logger="django.request"):
            client.get("/middleware_exceptions/view/")
            assert (
                "MiddlewareNotUsed('test_middlewares.test_exceptions."
                "MyMiddlewareWithExceptionMessage'): spam eggs" in caplog.text
            )

    def test_do_not_log_when_debug_is_false(self, settings, client, caplog):
        settings.DEBUG = False
        settings.MIDDLEWARE = ["test_middlewares.test_exceptions.MyMiddleware"]
        with caplog.at_level(logging.DEBUG, logger="django.request"):
            client.get("/middleware_exceptions/view/")
            assert not caplog.records

    async def test_async_and_sync_middleware_chain_async_call(
        self, settings, async_client, caplog
    ):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.SyncAndAsyncMiddleware",
            "test_middlewares.test_exceptions.MyMiddleware",
        ]
        with caplog.at_level(logging.DEBUG, logger="django.request"):
            response = await async_client.get("/middleware_exceptions/view/")
            assert response.content == b"OK"
            assert response.status_code == 200
            assert (
                "Asynchronous handler adapted for middleware "
                "test_middlewares.test_exceptions.MyMiddleware." in caplog.text
            )
            assert (
                "MiddlewareNotUsed: 'test_middlewares.test_exceptions.MyMiddleware'"
                in caplog.text
            )


class TestMiddlewareSyncAsync:
    @pytest.fixture(autouse=True)
    def setup(self, settings):
        settings.DEBUG = True
        settings.ROOT_URLCONF = "test_middlewares.urls"

    def test_async_middleware(self, settings, client, caplog):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.async_payment_middleware",
        ]
        with caplog.at_level(logging.DEBUG, "django.request"):
            response = client.get("/middleware_exceptions/view/")
            assert response.status_code == 402
            assert (
                "Synchronous handler adapted for middleware "
                "test_middlewares.middlewares.async_payment_middleware." in caplog.text
            )

    def test_not_sync_or_async_middleware(self, settings, client):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.NotSyncOrAsyncMiddleware",
        ]
        msg = (
            "Middleware "
            "test_middlewares.middlewares.NotSyncOrAsyncMiddleware must "
            "have at least one of sync_capable/async_capable set to True."
        )
        with pytest.raises(RuntimeError, match=msg):
            client.get("/middleware_exceptions/view/")

    async def test_async_middleware_async(self, settings, async_client, caplog):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.async_payment_middleware",
        ]
        with caplog.at_level("WARNING", "django.request"):
            response = await async_client.get("/middleware_exceptions/view/")
            assert response.status_code == 402
            assert "Payment Required: /middleware_exceptions/view/" in caplog.text

    def test_async_process_template_response_returns_none_with_sync_client(
        self, settings, client
    ):
        settings.DEBUG = False
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.AsyncNoTemplateResponseMiddleware",
        ]
        msg = (
            "AsyncNoTemplateResponseMiddleware.process_template_response "
            "didn't return an HttpResponse object."
        )
        with pytest.raises(ValueError, match=msg):
            client.get("/middleware_exceptions/template_response/")


class TestAsyncMiddleware:
    @pytest.fixture(autouse=True)
    def setup(self, settings):
        settings.ROOT_URLCONF = "test_middlewares.urls"

    async def test_process_template_response(self, settings, async_client):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.AsyncTemplateResponseMiddleware",
        ]
        response = await async_client.get("/middleware_exceptions/template_response/")
        assert (
            response.content == b"template_response OK\nAsyncTemplateResponseMiddleware"
        )

    async def test_process_template_response_returns_none(self, settings, async_client):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.AsyncNoTemplateResponseMiddleware",
        ]
        msg = (
            "AsyncNoTemplateResponseMiddleware.process_template_response "
            "didn't return an HttpResponse object. It returned None instead."
        )
        with pytest.raises(ValueError, match=msg):
            await async_client.get("/middleware_exceptions/template_response/")

    async def test_exception_in_render_passed_to_process_exception(
        self, settings, async_client
    ):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.AsyncProcessExceptionMiddleware",
        ]
        response = await async_client.get("/middleware_exceptions/exception_in_render/")
        assert response.content == b"Exception caught"

    async def test_exception_in_async_render_passed_to_process_exception(
        self, settings, async_client
    ):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.AsyncProcessExceptionMiddleware",
        ]
        response = await async_client.get(
            "/middleware_exceptions/async_exception_in_render/"
        )
        assert response.content == b"Exception caught"

    async def test_view_exception_handled_by_process_exception(
        self, settings, async_client
    ):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.AsyncProcessExceptionMiddleware",
        ]
        response = await async_client.get("/middleware_exceptions/error/")
        assert response.content == b"Exception caught"

    async def test_process_view_return_response(self, settings, async_client):
        settings.MIDDLEWARE = [
            "test_middlewares.middlewares.AsyncProcessViewMiddleware",
        ]
        response = await async_client.get("/middleware_exceptions/view/")
        assert response.content == b"Processed view normal_view"
