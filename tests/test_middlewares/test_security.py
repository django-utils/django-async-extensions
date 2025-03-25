import re

import pytest

from django.http import HttpResponse
from django.test import AsyncRequestFactory
from django.test.utils import override_settings


class TestSecurityMiddleware:
    @pytest.fixture
    def set_setting_fixture(self, request, settings):
        # request.param should be a list of [settings_name, value]
        setattr(settings, request.param[0], request.param[1])

    @pytest.fixture
    def hsts_seconds_fixture(self, request, settings):
        settings.SECURE_HSTS_SECONDS = request.param

    @pytest.fixture
    def hsts_with_subdomains_fixture(self, request, settings):
        settings.SECURE_HSTS_INCLUDE_SUBDOMAINS = request.param

    @pytest.fixture
    def ssl_redirect_fixture(self, request, settings):
        settings.SECURE_SSL_REDIRECT = request.param

    def middleware(self, *args, **kwargs):
        from django_async_extensions.middleware.security import AsyncSecurityMiddleware

        return AsyncSecurityMiddleware(self.response(*args, **kwargs))

    @property
    def secure_request_kwargs(self):
        return {"type": "https"}

    def response(self, *args, headers=None, **kwargs):
        async def get_response(req):
            response = HttpResponse(*args, **kwargs)
            if headers:
                for k, v in headers.items():
                    response.headers[k] = v
            return response

        return get_response

    async def process_response(self, *args, secure=False, request=None, **kwargs):
        request_kwargs = {}
        if secure:
            request_kwargs.update(self.secure_request_kwargs)
        if request is None:
            request = self.request.get("/some/url", secure=secure, **request_kwargs)
        ret = await self.middleware(*args, **kwargs).process_request(request)
        if ret:
            return ret
        return await self.middleware(*args, **kwargs)(request)

    request = AsyncRequestFactory()

    async def process_request(self, method, *args, secure=False, **kwargs):
        if secure:
            kwargs.update(self.secure_request_kwargs)
        req = getattr(self.request, method.lower())(*args, secure=secure, **kwargs)
        return await self.middleware().process_request(req)

    def test_middleware_instance_attributes(self, settings):
        middleware = self.middleware()
        assert middleware.sts_seconds == settings.SECURE_HSTS_SECONDS
        assert (
            middleware.sts_include_subdomains == settings.SECURE_HSTS_INCLUDE_SUBDOMAINS
        )
        assert middleware.sts_preload == settings.SECURE_HSTS_PRELOAD
        assert middleware.content_type_nosniff == settings.SECURE_CONTENT_TYPE_NOSNIFF
        assert middleware.redirect == settings.SECURE_SSL_REDIRECT
        assert middleware.redirect_host == settings.SECURE_SSL_HOST
        assert middleware.redirect_exempt == [
            re.compile(r) for r in settings.SECURE_REDIRECT_EXEMPT
        ]
        assert middleware.referrer_policy == settings.SECURE_REFERRER_POLICY
        assert (
            middleware.cross_origin_opener_policy
            == settings.SECURE_CROSS_ORIGIN_OPENER_POLICY
        )

    @pytest.mark.parametrize("hsts_seconds_fixture", [3600], indirect=True)
    async def test_sts_on(self, hsts_seconds_fixture):
        """
        With SECURE_HSTS_SECONDS=3600, the middleware adds
        "Strict-Transport-Security: max-age=3600" to the response.
        """
        response = await self.process_response(secure=True)
        assert response.headers["Strict-Transport-Security"] == "max-age=3600"

    @pytest.mark.parametrize("hsts_seconds_fixture", [3600], indirect=True)
    async def test_sts_already_present(self, hsts_seconds_fixture):
        """
        The middleware will not override a "Strict-Transport-Security" header
        already present in the response.
        """
        response = await self.process_response(
            secure=True, headers={"Strict-Transport-Security": "max-age=7200"}
        )
        assert response.headers["Strict-Transport-Security"] == "max-age=7200"

    @pytest.mark.parametrize("hsts_seconds_fixture", [3600], indirect=True)
    async def test_sts_only_if_secure(self, hsts_seconds_fixture):
        """
        The "Strict-Transport-Security" header is not added to responses going
        over an insecure connection.
        """
        response = await self.process_response(secure=False)
        assert "Strict-Transport-Security" not in response.headers

    @pytest.mark.parametrize("hsts_seconds_fixture", [0], indirect=True)
    async def test_sts_off(self, hsts_seconds_fixture):
        """
        With SECURE_HSTS_SECONDS=0, the middleware does not add a
        "Strict-Transport-Security" header to the response.
        """
        response = await self.process_response(secure=True)
        assert "Strict-Transport-Security" not in response.headers

    @pytest.mark.parametrize("hsts_seconds_fixture", [600], indirect=True)
    @pytest.mark.parametrize("hsts_with_subdomains_fixture", [True], indirect=True)
    async def test_sts_include_subdomains(
        self, hsts_seconds_fixture, hsts_with_subdomains_fixture
    ):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_INCLUDE_SUBDOMAINS
        True, the middleware adds a "Strict-Transport-Security" header with the
        "includeSubDomains" directive to the response.
        """
        response = await self.process_response(secure=True)
        assert (
            response.headers["Strict-Transport-Security"]
            == "max-age=600; includeSubDomains"
        )

    @pytest.mark.parametrize("hsts_seconds_fixture", [600], indirect=True)
    @pytest.mark.parametrize("hsts_with_subdomains_fixture", [False], indirect=True)
    async def test_sts_no_include_subdomains(
        self, hsts_seconds_fixture, hsts_with_subdomains_fixture
    ):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_INCLUDE_SUBDOMAINS
        False, the middleware adds a "Strict-Transport-Security" header without
        the "includeSubDomains" directive to the response.
        """
        response = await self.process_response(secure=True)
        assert response.headers["Strict-Transport-Security"] == "max-age=600"

    @pytest.mark.parametrize("hsts_seconds_fixture", [10886400], indirect=True)
    @pytest.mark.parametrize(
        "set_setting_fixture", [["SECURE_HSTS_PRELOAD", True]], indirect=True
    )
    async def test_sts_preload(self, hsts_seconds_fixture, set_setting_fixture):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_PRELOAD True, the
        middleware adds a "Strict-Transport-Security" header with the "preload"
        directive to the response.
        """
        response = await self.process_response(secure=True)
        assert (
            response.headers["Strict-Transport-Security"] == "max-age=10886400; preload"
        )

    @pytest.mark.parametrize("hsts_seconds_fixture", [10886400], indirect=True)
    @pytest.mark.parametrize("hsts_with_subdomains_fixture", [True], indirect=True)
    @pytest.mark.parametrize(
        "set_setting_fixture", [["SECURE_HSTS_PRELOAD", True]], indirect=True
    )
    async def test_sts_subdomains_and_preload(
        self, hsts_seconds_fixture, hsts_with_subdomains_fixture, set_setting_fixture
    ):
        """
        With SECURE_HSTS_SECONDS non-zero, SECURE_HSTS_INCLUDE_SUBDOMAINS and
        SECURE_HSTS_PRELOAD True, the middleware adds a "Strict-Transport-Security"
        header containing both the "includeSubDomains" and "preload" directives
        to the response.
        """
        response = await self.process_response(secure=True)
        assert (
            response.headers["Strict-Transport-Security"]
            == "max-age=10886400; includeSubDomains; preload"
        )

    @pytest.mark.parametrize("hsts_seconds_fixture", [10886400], indirect=True)
    @pytest.mark.parametrize(
        "set_setting_fixture", [["SECURE_HSTS_PRELOAD", False]], indirect=True
    )
    async def test_sts_no_preload(self, hsts_seconds_fixture, set_setting_fixture):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_PRELOAD
        False, the middleware adds a "Strict-Transport-Security" header without
        the "preload" directive to the response.
        """
        response = await self.process_response(secure=True)
        assert response.headers["Strict-Transport-Security"] == "max-age=10886400"

    @pytest.mark.parametrize(
        "set_setting_fixture", [["SECURE_CONTENT_TYPE_NOSNIFF", True]], indirect=True
    )
    async def test_content_type_on(self, set_setting_fixture):
        """
        With SECURE_CONTENT_TYPE_NOSNIFF set to True, the middleware adds
        "X-Content-Type-Options: nosniff" header to the response.
        """
        response = await self.process_response()
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.parametrize(
        "set_setting_fixture", [["SECURE_CONTENT_TYPE_NOSNIFF", True]], indirect=True
    )
    async def test_content_type_already_present(self, set_setting_fixture):
        """
        The middleware will not override an "X-Content-Type-Options" header
        already present in the response.
        """
        response = await self.process_response(
            secure=True, headers={"X-Content-Type-Options": "foo"}
        )
        assert response.headers["X-Content-Type-Options"] == "foo"

    @pytest.mark.parametrize(
        "set_setting_fixture", [["SECURE_CONTENT_TYPE_NOSNIFF", False]], indirect=True
    )
    async def test_content_type_off(self, set_setting_fixture):
        """
        With SECURE_CONTENT_TYPE_NOSNIFF False, the middleware does not add an
        "X-Content-Type-Options" header to the response.
        """
        response = await self.process_response()
        assert "X-Content-Type-Options" not in response.headers

    @pytest.mark.parametrize("ssl_redirect_fixture", [True], indirect=True)
    async def test_ssl_redirect_on(self, ssl_redirect_fixture):
        """
        With SECURE_SSL_REDIRECT True, the middleware redirects any non-secure
        requests to the https:// version of the same URL.
        """
        ret = await self.process_request("get", "/some/url?query=string")
        assert ret.status_code == 301
        assert ret["Location"] == "https://testserver/some/url?query=string"

    @pytest.mark.parametrize("ssl_redirect_fixture", [True], indirect=True)
    async def test_no_redirect_ssl(self, ssl_redirect_fixture):
        """
        The middleware does not redirect secure requests.
        """
        ret = await self.process_request("get", "/some/url", secure=True)
        assert ret is None

    @pytest.mark.parametrize(
        "set_setting_fixture",
        [["SECURE_REDIRECT_EXEMPT", ["^insecure/"]]],
        indirect=True,
    )
    @pytest.mark.parametrize("ssl_redirect_fixture", [True], indirect=True)
    async def test_redirect_exempt(self, set_setting_fixture, ssl_redirect_fixture):
        """
        The middleware does not redirect requests with URL path matching an
        exempt pattern.
        """
        ret = await self.process_request("get", "/insecure/page")
        assert ret is None

    @pytest.mark.parametrize(
        "set_setting_fixture",
        [["SECURE_SSL_HOST", "secure.example.com"]],
        indirect=True,
    )
    @pytest.mark.parametrize("ssl_redirect_fixture", [True], indirect=True)
    async def test_redirect_ssl_host(self, ssl_redirect_fixture, set_setting_fixture):
        """
        The middleware redirects to SECURE_SSL_HOST if given.
        """
        ret = await self.process_request("get", "/some/url")
        assert ret.status_code == 301
        assert ret["Location"] == "https://secure.example.com/some/url"

    @pytest.mark.parametrize("ssl_redirect_fixture", [False], indirect=True)
    async def test_ssl_redirect_off(self, ssl_redirect_fixture):
        """
        With SECURE_SSL_REDIRECT False, the middleware does not redirect.
        """
        ret = await self.process_request("get", "/some/url")
        assert ret is None

    @pytest.mark.parametrize(
        "set_setting_fixture", [["SECURE_REFERRER_POLICY", None]], indirect=True
    )
    async def test_referrer_policy_off(self, set_setting_fixture):
        """
        With SECURE_REFERRER_POLICY set to None, the middleware does not add a
        "Referrer-Policy" header to the response.
        """
        response = await self.process_response()
        assert "Referrer-Policy" not in response.headers

    async def test_referrer_policy_on(self, subtests):
        """
        With SECURE_REFERRER_POLICY set to a valid value, the middleware adds a
        "Referrer-Policy" header to the response.
        """
        tests = (
            ("strict-origin", "strict-origin"),
            ("strict-origin,origin", "strict-origin,origin"),
            ("strict-origin, origin", "strict-origin,origin"),
            (["strict-origin", "origin"], "strict-origin,origin"),
            (("strict-origin", "origin"), "strict-origin,origin"),
        )
        for value, expected in tests:
            with (
                subtests.test(value=value),
                override_settings(SECURE_REFERRER_POLICY=value),
            ):
                response = await self.process_response()
                assert response.headers["Referrer-Policy"] == expected

    @pytest.mark.parametrize(
        "set_setting_fixture",
        [["SECURE_REFERRER_POLICY", "strict-origin"]],
        indirect=True,
    )
    async def test_referrer_policy_already_present(self, set_setting_fixture):
        """
        The middleware will not override a "Referrer-Policy" header already
        present in the response.
        """
        response = await self.process_response(
            headers={"Referrer-Policy": "unsafe-url"}
        )
        assert response.headers["Referrer-Policy"] == "unsafe-url"

    @pytest.mark.parametrize(
        "set_setting_fixture",
        [["SECURE_CROSS_ORIGIN_OPENER_POLICY", None]],
        indirect=True,
    )
    async def test_coop_off(self, set_setting_fixture):
        """
        With SECURE_CROSS_ORIGIN_OPENER_POLICY set to None, the middleware does
        not add a "Cross-Origin-Opener-Policy" header to the response.
        """
        assert "Cross-Origin-Opener-Policy" not in await self.process_response()

    async def test_coop_default(self):
        """SECURE_CROSS_ORIGIN_OPENER_POLICY defaults to same-origin."""
        response = await self.process_response()
        assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"

    async def test_coop_on(self, subtests):
        """
        With SECURE_CROSS_ORIGIN_OPENER_POLICY set to a valid value, the
        middleware adds a "Cross-Origin_Opener-Policy" header to the response.
        """
        tests = ["same-origin", "same-origin-allow-popups", "unsafe-none"]
        for value in tests:
            with (
                subtests.test(value=value),
                override_settings(
                    SECURE_CROSS_ORIGIN_OPENER_POLICY=value,
                ),
            ):
                response = await self.process_response()
                assert response.headers["Cross-Origin-Opener-Policy"] == value

    @pytest.mark.parametrize(
        "set_setting_fixture",
        [["SECURE_CROSS_ORIGIN_OPENER_POLICY", "unsafe-none"]],
        indirect=True,
    )
    async def test_coop_already_present(self, set_setting_fixture):
        """
        The middleware doesn't override a "Cross-Origin-Opener-Policy" header
        already present in the response.
        """
        response = await self.process_response(
            headers={"Cross-Origin-Opener-Policy": "same-origin"}
        )
        assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
