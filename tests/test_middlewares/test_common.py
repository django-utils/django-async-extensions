import re
from urllib.parse import quote
import pytest
from django.core import mail
from django.core.exceptions import PermissionDenied

from django.http import (
    HttpResponse,
    HttpResponseNotFound,
    HttpResponsePermanentRedirect,
    StreamingHttpResponse,
    HttpResponseRedirect,
)
from django.test import AsyncRequestFactory, AsyncClient

from django_async_extensions.amiddleware.common import (
    AsyncCommonMiddleware,
    AsyncBrokenLinkEmailsMiddleware,
)

client = AsyncClient()


async def get_response_empty(request):
    return HttpResponse()


async def get_response_404(request):
    return HttpResponseNotFound()


@pytest.fixture
def append_slash_fixture(request, settings):
    old_append_slash = settings.APPEND_SLASH
    settings.APPEND_SLASH = request.param

    yield settings
    settings.APPEND_SLASH = old_append_slash


class TestCommonMiddleware:
    rf = AsyncRequestFactory()

    @pytest.fixture(autouse=True)
    def urlconf_setting_set(self, settings):
        old_urlconf = settings.ROOT_URLCONF
        settings.ROOT_URLCONF = "test_middlewares.urls"
        yield settings
        settings.ROOT_URLCONF = old_urlconf

    @pytest.fixture
    def set_setting_fixture(self, request, settings):
        # request.param should be a list of [settings_name, value]
        old_setting = getattr(settings, request.param[0])
        setattr(settings, request.param[0], request.param[1])
        yield settings
        setattr(settings, request.param[0], old_setting)

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_have_slash(self, append_slash_fixture):
        """
        URLs with slashes should go unmolested.
        """
        request = self.rf.get("/slash/")
        assert (
            await AsyncCommonMiddleware(get_response_404).process_request(request)
            is None
        )
        response = await AsyncCommonMiddleware(get_response_404)(request)
        assert response.status_code == 404

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_slashless_resource(self, append_slash_fixture):
        """
        Matches to explicit slashless URLs should go unmolested.
        """

        async def get_response(req):
            return HttpResponse("Here's the text of the web page.")

        request = self.rf.get("/noslash")
        assert (
            await AsyncCommonMiddleware(get_response).process_request(request) is None
        )
        response = await AsyncCommonMiddleware(get_response)(request)
        assert response.content == b"Here's the text of the web page."

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_slashless_unknown(self, append_slash_fixture):
        """
        APPEND_SLASH should not redirect to unknown resources.
        """
        request = self.rf.get("/unknown")
        response = await AsyncCommonMiddleware(get_response_404)(request)
        assert response.status_code == 404

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_redirect(self, append_slash_fixture, settings):
        """
        APPEND_SLASH should redirect slashless URLs to a valid pattern.
        """
        request = self.rf.get("/slash")
        r = await AsyncCommonMiddleware(get_response_empty).process_request(request)
        assert r is None
        response = HttpResponseNotFound()
        r = await AsyncCommonMiddleware(get_response_empty).process_response(
            request, response
        )
        assert r.status_code == 301
        assert r.url == "/slash/"

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_redirect_querystring(self, append_slash_fixture):
        """
        APPEND_SLASH should preserve querystrings when redirecting.
        """
        request = self.rf.get("/slash?test=1")
        resp = await AsyncCommonMiddleware(get_response_404)(request)
        assert resp.url == "/slash/?test=1"

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_redirect_querystring_have_slash(
        self, append_slash_fixture
    ):
        """
        APPEND_SLASH should append slash to path when redirecting a request
        with a querystring ending with slash.
        """
        request = self.rf.get("/slash?test=slash/")
        resp = await AsyncCommonMiddleware(get_response_404)(request)
        assert isinstance(resp, HttpResponsePermanentRedirect)
        assert resp.url == "/slash/?test=slash/"

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    @pytest.mark.parametrize("set_setting_fixture", [["DEBUG", True]], indirect=True)
    async def test_append_slash_no_redirect_in_DEBUG(
        self, append_slash_fixture, set_setting_fixture
    ):
        """
        While in debug mode, an exception is raised with a warning
        when a failed attempt is made to DELETE, POST, PUT, or PATCH to an URL
        which would normally be redirected to a slashed version.
        """
        msg = "maintaining %s data. Change your form to point to testserver/slash/"
        request = self.rf.get("/slash")
        request.method = "POST"
        with pytest.raises(RuntimeError, match=msg % request.method):
            await AsyncCommonMiddleware(get_response_404)(request)
        request = self.rf.get("/slash")
        request.method = "PUT"
        with pytest.raises(RuntimeError, match=msg % request.method):
            await AsyncCommonMiddleware(get_response_404)(request)
        request = self.rf.get("/slash")
        request.method = "PATCH"
        with pytest.raises(RuntimeError, match=msg % request.method):
            await AsyncCommonMiddleware(get_response_404)(request)
        request = self.rf.delete("/slash")
        with pytest.raises(RuntimeError, match=msg % request.method):
            await AsyncCommonMiddleware(get_response_404)(request)

    @pytest.mark.parametrize("append_slash_fixture", [False], indirect=True)
    async def test_append_slash_disabled(self, append_slash_fixture):
        """
        Disabling append slash functionality should leave slashless URLs alone.
        """
        request = self.rf.get("/slash")
        response = await AsyncCommonMiddleware(get_response_404)(request)
        assert response.status_code == 404

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_opt_out(self, append_slash_fixture):
        """
        Views marked with @no_append_slash should be left alone.
        """
        request = self.rf.get("/sensitive_fbv")
        response = await AsyncCommonMiddleware(get_response_404)(request)
        assert response.status_code == 404

        request = self.rf.get("/sensitive_cbv")
        response = await AsyncCommonMiddleware(get_response_404)(request)
        assert response.status_code == 404

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_quoted(self, append_slash_fixture):
        """
        URLs which require quoting should be redirected to their slash version.
        """
        request = self.rf.get(quote("/needsquoting#"))
        r = await AsyncCommonMiddleware(get_response_404)(request)
        assert r.status_code == 301
        assert r.url == "/needsquoting%23/"

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_leading_slashes(self, append_slash_fixture):
        """
        Paths starting with two slashes are escaped to prevent open redirects.
        If there's a URL pattern that allows paths to start with two slashes, a
        request with path //evil.com must not redirect to //evil.com/ (appended
        slash) which is a schemaless absolute URL. The browser would navigate
        to evil.com/.
        """
        # Use 4 slashes because of RequestFactory behavior.
        request = self.rf.get("////evil.com/security")
        r = await AsyncCommonMiddleware(get_response_404).process_request(request)
        assert r is None
        response = HttpResponseNotFound()
        r = await AsyncCommonMiddleware(get_response_404).process_response(
            request, response
        )
        assert r.status_code == 301
        assert r.url == "/%2Fevil.com/security/"
        r = await AsyncCommonMiddleware(get_response_404)(request)
        assert r.status_code == 301
        assert r.url == "/%2Fevil.com/security/"

    @pytest.mark.parametrize("append_slash_fixture", [False], indirect=True)
    @pytest.mark.parametrize(
        "set_setting_fixture", [["PREPEND_WWW", True]], indirect=True
    )
    async def test_prepend_www(self, append_slash_fixture, set_setting_fixture):
        request = self.rf.get("/path/")
        r = await AsyncCommonMiddleware(get_response_empty).process_request(request)
        assert r.status_code == 301
        assert r.url == "http://www.testserver/path/"

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    @pytest.mark.parametrize(
        "set_setting_fixture", [["PREPEND_WWW", True]], indirect=True
    )
    async def test_prepend_www_append_slash_have_slash(
        self, append_slash_fixture, set_setting_fixture
    ):
        request = self.rf.get("/slash/")
        r = await AsyncCommonMiddleware(get_response_empty).process_request(request)
        assert r.status_code == 301
        assert r.url == "http://www.testserver/slash/"

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    @pytest.mark.parametrize(
        "set_setting_fixture", [["PREPEND_WWW", True]], indirect=True
    )
    async def test_prepend_www_append_slash_slashless(
        self, append_slash_fixture, set_setting_fixture
    ):
        request = self.rf.get("/slash")
        r = await AsyncCommonMiddleware(get_response_empty).process_request(request)
        assert r.status_code == 301
        assert r.url == "http://www.testserver/slash/"

    # The following tests examine expected behavior given a custom URLconf that
    # overrides the default one through the request object.

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_have_slash_custom_urlconf(self, append_slash_fixture):
        """
        URLs with slashes should go unmolested.
        """
        request = self.rf.get("/customurlconf/slash/")
        request.urlconf = "test_middlewares.extra_urls"
        assert (
            await AsyncCommonMiddleware(get_response_404).process_request(request)
            is None
        )
        response = await AsyncCommonMiddleware(get_response_404)(request)
        assert response.status_code == 404

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_slashless_resource_custom_urlconf(
        self, append_slash_fixture
    ):
        """
        Matches to explicit slashless URLs should go unmolested.
        """

        async def get_response(req):
            return HttpResponse("web content")

        request = self.rf.get("/customurlconf/noslash")
        request.urlconf = "test_middlewares.extra_urls"
        assert (
            await AsyncCommonMiddleware(get_response).process_request(request) is None
        )
        response = await AsyncCommonMiddleware(get_response)(request)
        assert response.content == b"web content"

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_slashless_unknown_custom_urlconf(
        self, append_slash_fixture
    ):
        """
        APPEND_SLASH should not redirect to unknown resources.
        """
        request = self.rf.get("/customurlconf/unknown")
        request.urlconf = "test_middlewares.extra_urls"
        assert (
            await AsyncCommonMiddleware(get_response_404).process_request(request)
            is None
        )
        response = await AsyncCommonMiddleware(get_response_404)(request)
        assert response.status_code == 404

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_redirect_custom_urlconf(self, append_slash_fixture):
        """
        APPEND_SLASH should redirect slashless URLs to a valid pattern.
        """
        request = self.rf.get("/customurlconf/slash")
        request.urlconf = "test_middlewares.extra_urls"
        r = await AsyncCommonMiddleware(get_response_404)(request)
        assert r, (
            "CommonMiddleware failed to return APPEND_SLASH redirect"
            " using request.urlconf"
        )

        assert r.status_code == 301
        assert r.url == "/customurlconf/slash/"

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    @pytest.mark.parametrize("set_setting_fixture", [["DEBUG", True]], indirect=True)
    async def test_append_slash_no_redirect_on_POST_in_DEBUG_custom_urlconf(
        self, append_slash_fixture, set_setting_fixture
    ):
        """
        While in debug mode, an exception is raised with a warning
        when a failed attempt is made to POST to an URL which would normally be
        redirected to a slashed version.
        """
        request = self.rf.get("/customurlconf/slash")
        request.urlconf = "test_middlewares.extra_urls"
        request.method = "POST"
        with pytest.raises(RuntimeError, match="end in a slash"):
            await AsyncCommonMiddleware(get_response_404)(request)

    @pytest.mark.parametrize("append_slash_fixture", [False], indirect=True)
    async def test_append_slash_disabled_custom_urlconf(self, append_slash_fixture):
        """
        Disabling append slash functionality should leave slashless URLs alone.
        """
        request = self.rf.get("/customurlconf/slash")
        request.urlconf = "test_middlewares.extra_urls"
        assert (
            await AsyncCommonMiddleware(get_response_404).process_request(request)
            is None
        )
        response = await AsyncCommonMiddleware(get_response_404)(request)
        assert response.status_code, 404

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_append_slash_quoted_custom_urlconf(self, append_slash_fixture):
        """
        URLs which require quoting should be redirected to their slash version.
        """
        request = self.rf.get(quote("/customurlconf/needsquoting#"))
        request.urlconf = "test_middlewares.extra_urls"
        r = await AsyncCommonMiddleware(get_response_404)(request)
        assert r is not None, (
            "CommonMiddleware failed to return APPEND_SLASH"
            " redirect using request.urlconf"
        )

        assert r.status_code == 301
        assert r.url == "/customurlconf/needsquoting%23/"

    @pytest.mark.parametrize("append_slash_fixture", [False], indirect=True)
    @pytest.mark.parametrize(
        "set_setting_fixture", [["PREPEND_WWW", True]], indirect=True
    )
    async def test_prepend_www_custom_urlconf(
        self, append_slash_fixture, set_setting_fixture
    ):
        request = self.rf.get("/customurlconf/path/")
        request.urlconf = "test_middlewares.extra_urls"
        r = await AsyncCommonMiddleware(get_response_empty).process_request(request)
        assert r.status_code == 301
        assert r.url == "http://www.testserver/customurlconf/path/"

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    @pytest.mark.parametrize(
        "set_setting_fixture", [["PREPEND_WWW", True]], indirect=True
    )
    async def test_prepend_www_append_slash_have_slash_custom_urlconf(
        self, append_slash_fixture, set_setting_fixture
    ):
        request = self.rf.get("/customurlconf/slash/")
        request.urlconf = "test_middlewares.extra_urls"
        r = await AsyncCommonMiddleware(get_response_empty).process_request(request)
        assert r.status_code == 301
        assert r.url == "http://www.testserver/customurlconf/slash/"

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    @pytest.mark.parametrize(
        "set_setting_fixture", [["PREPEND_WWW", True]], indirect=True
    )
    async def test_prepend_www_append_slash_slashless_custom_urlconf(
        self, append_slash_fixture, set_setting_fixture
    ):
        request = self.rf.get("/customurlconf/slash")
        request.urlconf = "test_middlewares.extra_urls"
        r = await AsyncCommonMiddleware(get_response_empty).process_request(request)
        assert r.status_code == 301
        assert r.url == "http://www.testserver/customurlconf/slash/"

    # Tests for the Content-Length header

    async def test_content_length_header_added(self):
        async def get_response(req):
            response = HttpResponse("content")
            assert b"Content-Length" not in response.headers
            return response

        response = await AsyncCommonMiddleware(get_response)(self.rf.get("/"))
        assert int(response.headers["Content-Length"]) == len(response.content)

    async def test_content_length_header_not_added_for_streaming_response(self):
        async def get_response(req):
            response = StreamingHttpResponse("content")
            assert b"Content-Length" not in response
            return response

        response = await AsyncCommonMiddleware(get_response)(self.rf.get("/"))
        assert b"Content-Length" not in response

    async def test_content_length_header_not_changed(self):
        bad_content_length = 500

        async def get_response(req):
            response = HttpResponse()
            response.headers["Content-Length"] = bad_content_length
            return response

        response = await AsyncCommonMiddleware(get_response)(self.rf.get("/"))
        assert int(response.headers["Content-Length"]) == bad_content_length

    # Other tests

    @pytest.mark.parametrize(
        "set_setting_fixture",
        [["DISALLOWED_USER_AGENTS", [re.compile(r"foo")]]],
        indirect=True,
    )
    async def test_disallowed_user_agents(self, set_setting_fixture):
        request = self.rf.get("/slash")
        request.META["HTTP_USER_AGENT"] = "foo"
        with pytest.raises(PermissionDenied, match="Forbidden user agent"):
            await AsyncCommonMiddleware(get_response_empty).process_request(request)

    async def test_non_ascii_query_string_does_not_crash(self):
        """Regression test for #15152"""
        request = self.rf.get("/slash")
        request.META["QUERY_STRING"] = "drink=café"
        r = await AsyncCommonMiddleware(get_response_empty).process_request(request)
        assert r is None
        response = HttpResponseNotFound()
        r = await AsyncCommonMiddleware(get_response_empty).process_response(
            request, response
        )
        assert r.status_code == 301

    async def test_response_redirect_class(self):
        request = self.rf.get("/slash")
        r = await AsyncCommonMiddleware(get_response_404)(request)
        assert r.status_code == 301
        assert r.url == "/slash/"
        assert isinstance(r, HttpResponsePermanentRedirect)

    async def test_response_redirect_class_subclass(self):
        class MyCommonMiddleware(AsyncCommonMiddleware):
            response_redirect_class = HttpResponseRedirect

        request = self.rf.get("/slash")
        r = await MyCommonMiddleware(get_response_404)(request)
        assert r.status_code == 302
        assert r.url == "/slash/"
        assert isinstance(r, HttpResponseRedirect)


class TestBrokenLinkEmailsMiddleware:
    rf = AsyncRequestFactory()

    @pytest.fixture(autouse=True)
    def setting_fixture(self, settings):
        old_ignorable_404_urls = settings.IGNORABLE_404_URLS
        old_managers = settings.MANAGERS
        settings.IGNORABLE_404_URLS = [re.compile(r"foo")]
        settings.MANAGERS = [("PHD", "PHB@dilbert.com")]
        yield settings
        settings.IGNORABLE_404_URLS = old_ignorable_404_urls
        settings.MANAGERS = old_managers

    @pytest.fixture(autouse=True)
    def setup(self):
        self.req = self.rf.get("/regular_url/that/does/not/exist")

    async def get_response(self, req):
        return await client.get(req.path)

    async def test_404_error_reporting(self):
        self.req.META["HTTP_REFERER"] = "/another/url/"
        await AsyncBrokenLinkEmailsMiddleware(self.get_response)(self.req)
        assert len(mail.outbox) == 1
        assert "Broken" in mail.outbox[0].subject

    async def test_404_error_reporting_no_referer(self):
        await AsyncBrokenLinkEmailsMiddleware(self.get_response)(self.req)
        assert len(mail.outbox) == 0

    async def test_404_error_reporting_ignored_url(self):
        self.req.path = self.req.path_info = "foo_url/that/does/not/exist"
        await AsyncBrokenLinkEmailsMiddleware(self.get_response)(self.req)
        assert len(mail.outbox) == 0

    async def test_custom_request_checker(self):
        class SubclassedMiddleware(AsyncBrokenLinkEmailsMiddleware):
            ignored_user_agent_patterns = (
                re.compile(r"Spider.*"),
                re.compile(r"Robot.*"),
            )

            def is_ignorable_request(self, request, uri, domain, referer):
                """Check user-agent in addition to normal checks."""
                if super().is_ignorable_request(request, uri, domain, referer):
                    return True
                user_agent = request.META["HTTP_USER_AGENT"]
                return any(
                    pattern.search(user_agent)
                    for pattern in self.ignored_user_agent_patterns
                )

        self.req.META["HTTP_REFERER"] = "/another/url/"
        self.req.META["HTTP_USER_AGENT"] = "Spider machine 3.4"
        await SubclassedMiddleware(self.get_response)(self.req)
        assert len(mail.outbox) == 0
        self.req.META["HTTP_USER_AGENT"] = "My user agent"
        await SubclassedMiddleware(self.get_response)(self.req)
        assert len(mail.outbox) == 1

    async def test_referer_equal_to_requested_url(self, settings):
        """
        Some bots set the referer to the current URL to avoid being blocked by
        an referer check (#25302).
        """
        self.req.META["HTTP_REFERER"] = self.req.path
        await AsyncBrokenLinkEmailsMiddleware(self.get_response)(self.req)
        assert len(mail.outbox) == 0

        # URL with scheme and domain should also be ignored
        self.req.META["HTTP_REFERER"] = "http://testserver%s" % self.req.path
        await AsyncBrokenLinkEmailsMiddleware(self.get_response)(self.req)
        assert len(mail.outbox) == 0

        # URL with a different scheme should be ignored as well because bots
        # tend to use http:// in referers even when browsing HTTPS websites.
        self.req.META["HTTP_X_PROTO"] = "https"
        self.req.META["SERVER_PORT"] = 443
        settings.SECURE_PROXY_SSL_HEADER = ("HTTP_X_PROTO", "https")
        await AsyncBrokenLinkEmailsMiddleware(self.get_response)(self.req)
        assert len(mail.outbox) == 0

    async def test_referer_equal_to_requested_url_on_another_domain(self):
        self.req.META["HTTP_REFERER"] = "http://anotherserver%s" % self.req.path
        await AsyncBrokenLinkEmailsMiddleware(self.get_response)(self.req)
        assert len(mail.outbox) == 1

    @pytest.mark.parametrize("append_slash_fixture", [True], indirect=True)
    async def test_referer_equal_to_requested_url_without_trailing_slash_with_append_slash(  # noqa: E501
        self, append_slash_fixture
    ):
        self.req.path = self.req.path_info = "/regular_url/that/does/not/exist/"
        self.req.META["HTTP_REFERER"] = self.req.path_info[:-1]
        await AsyncBrokenLinkEmailsMiddleware(self.get_response)(self.req)
        assert len(mail.outbox) == 0

    @pytest.mark.parametrize("append_slash_fixture", [False], indirect=True)
    async def test_referer_equal_to_requested_url_without_trailing_slash_with_no_append_slash(  # noqa: E501
        self, append_slash_fixture
    ):
        self.req.path = self.req.path_info = "/regular_url/that/does/not/exist/"
        self.req.META["HTTP_REFERER"] = self.req.path_info[:-1]
        await AsyncBrokenLinkEmailsMiddleware(self.get_response)(self.req)
        assert len(mail.outbox) == 1
