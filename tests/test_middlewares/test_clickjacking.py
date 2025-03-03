from django.http import HttpResponse, HttpResponseNotFound, HttpRequest

from django_async_extensions.amiddleware.clickjacking import (
    AsyncXFrameOptionsMiddleware,
)


async def get_response_empty(request):
    return HttpResponse()


async def get_response_404(request):
    return HttpResponseNotFound()


class TestXFrameOptionsMiddleware:
    """
    Tests for the X-Frame-Options clickjacking prevention middleware.
    """

    async def test_same_origin(self, settings):
        """
        The X_FRAME_OPTIONS setting can be set to SAMEORIGIN to have the
        middleware use that value for the HTTP header.
        """
        settings.X_FRAME_OPTIONS = "SAMEORIGIN"
        r = await AsyncXFrameOptionsMiddleware(get_response_empty)(HttpRequest())
        assert r.headers["X-Frame-Options"] == "SAMEORIGIN"

        settings.X_FRAME_OPTIONS = "sameorigin"
        r = await AsyncXFrameOptionsMiddleware(get_response_empty)(HttpRequest())
        assert r.headers["X-Frame-Options"] == "SAMEORIGIN"

    async def test_deny(self, settings):
        """
        The X_FRAME_OPTIONS setting can be set to DENY to have the middleware
        use that value for the HTTP header.
        """
        settings.X_FRAME_OPTIONS = "DENY"
        r = await AsyncXFrameOptionsMiddleware(get_response_empty)(HttpRequest())
        assert r.headers["X-Frame-Options"] == "DENY"

        settings.X_FRAME_OPTIONS = "deny"
        r = await AsyncXFrameOptionsMiddleware(get_response_empty)(HttpRequest())
        assert r.headers["X-Frame-Options"] == "DENY"

    async def test_defaults_sameorigin(self, settings):
        """
        If the X_FRAME_OPTIONS setting is not set then it defaults to
        DENY.
        """
        settings.X_FRAME_OPTIONS = None
        del settings.X_FRAME_OPTIONS  # restored by override_settings
        r = await AsyncXFrameOptionsMiddleware(get_response_empty)(HttpRequest())
        assert r.headers["X-Frame-Options"] == "DENY"

    async def test_dont_set_if_set(self, settings):
        """
        If the X-Frame-Options header is already set then the middleware does
        not attempt to override it.
        """

        async def same_origin_response(request):
            response = HttpResponse()
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            return response

        async def deny_response(request):
            response = HttpResponse()
            response.headers["X-Frame-Options"] = "DENY"
            return response

        settings.X_FRAME_OPTIONS = "DENY"
        r = await AsyncXFrameOptionsMiddleware(same_origin_response)(HttpRequest())
        assert r.headers["X-Frame-Options"] == "SAMEORIGIN"

        settings.X_FRAME_OPTIONS = "SAMEORIGIN"
        r = await AsyncXFrameOptionsMiddleware(deny_response)(HttpRequest())
        assert r.headers["X-Frame-Options"] == "DENY"

    async def test_response_exempt(self, settings):
        """
        If the response has an xframe_options_exempt attribute set to False
        then it still sets the header, but if it's set to True then it doesn't.
        """

        async def xframe_exempt_response(request):
            response = HttpResponse()
            response.xframe_options_exempt = True
            return response

        async def xframe_not_exempt_response(request):
            response = HttpResponse()
            response.xframe_options_exempt = False
            return response

        settings.X_FRAME_OPTIONS = "SAMEORIGIN"
        r = await AsyncXFrameOptionsMiddleware(xframe_not_exempt_response)(
            HttpRequest()
        )
        assert r.headers["X-Frame-Options"] == "SAMEORIGIN"

        r = await AsyncXFrameOptionsMiddleware(xframe_exempt_response)(HttpRequest())
        assert r.headers.get("X-Frame-Options") is None

    async def test_is_extendable(self, settings):
        """
        The XFrameOptionsMiddleware method that determines the X-Frame-Options
        header value can be overridden based on something in the request or
        response.
        """

        class OtherXFrameOptionsMiddleware(AsyncXFrameOptionsMiddleware):
            # This is just an example for testing purposes...
            def get_xframe_options_value(self, request, response):
                if getattr(request, "sameorigin", False):
                    return "SAMEORIGIN"
                if getattr(response, "sameorigin", False):
                    return "SAMEORIGIN"
                return "DENY"

        async def same_origin_response(request):
            response = HttpResponse()
            response.sameorigin = True
            return response

        settings.X_FRAME_OPTIONS = "DENY"
        r = await OtherXFrameOptionsMiddleware(same_origin_response)(HttpRequest())
        assert r.headers["X-Frame-Options"] == "SAMEORIGIN"

        request = HttpRequest()
        request.sameorigin = True
        r = await OtherXFrameOptionsMiddleware(get_response_empty)(request)
        assert r.headers["X-Frame-Options"] == "SAMEORIGIN"

        settings.X_FRAME_OPTIONS = "SAMEORIGIN"
        r = await OtherXFrameOptionsMiddleware(get_response_empty)(HttpRequest())
        assert r.headers["X-Frame-Options"] == "DENY"
