import pytest

from django.http import StreamingHttpResponse, HttpResponse
from django.test import AsyncRequestFactory, AsyncClient

from django_async_extensions.amiddleware.http import AsyncConditionalGetMiddleware


client = AsyncClient()


@pytest.fixture(autouse=True)
def urlconf_setting_set(settings):
    old_urlconf = settings.ROOT_URLCONF
    settings.ROOT_URLCONF = "test_middlewares.cond_get_urls"
    yield settings
    settings.ROOT_URLCONF = old_urlconf


class TestConditionalGetMiddleware:
    request_factory = AsyncRequestFactory()

    @pytest.fixture(autouse=True)
    def setup(self):
        self.req = self.request_factory.get("/")
        self.resp_headers = {}

    async def get_response(self, req):
        resp = await client.get(req.path_info)
        for key, value in self.resp_headers.items():
            resp[key] = value
        return resp

    # Tests for the ETag header

    async def test_middleware_calculates_etag(self):
        resp = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        assert resp.status_code == 200
        assert "" != resp["ETag"]

    async def test_middleware_wont_overwrite_etag(self):
        self.resp_headers["ETag"] = "eggs"
        resp = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        assert resp.status_code == 200
        assert "eggs" == resp["ETag"]

    async def test_no_etag_streaming_response(self):
        async def get_response(req):
            return StreamingHttpResponse(["content"])

        response = await AsyncConditionalGetMiddleware(get_response)(self.req)
        assert response.has_header("ETag") is False

    async def test_no_etag_response_empty_content(self):
        async def get_response(req):
            return HttpResponse()

        response = await AsyncConditionalGetMiddleware(get_response)(self.req)
        assert response.has_header("ETag") is False

    async def test_no_etag_no_store_cache(self):
        self.resp_headers["Cache-Control"] = "No-Cache, No-Store, Max-age=0"
        response = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        assert response.has_header("ETag") is False

    async def test_etag_extended_cache_control(self):
        self.resp_headers["Cache-Control"] = 'my-directive="my-no-store"'
        response = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        assert response.has_header("ETag")

    async def test_if_none_match_and_no_etag(self):
        self.req.META["HTTP_IF_NONE_MATCH"] = "spam"
        resp = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        assert resp.status_code == 200

    async def test_no_if_none_match_and_etag(self):
        self.resp_headers["ETag"] = "eggs"
        resp = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        assert resp.status_code == 200

    async def test_if_none_match_and_same_etag(self):
        self.req.META["HTTP_IF_NONE_MATCH"] = '"spam"'
        self.resp_headers["ETag"] = '"spam"'
        resp = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        assert resp.status_code == 304

    async def test_if_none_match_and_different_etag(self):
        self.req.META["HTTP_IF_NONE_MATCH"] = "spam"
        self.resp_headers["ETag"] = "eggs"
        resp = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        assert resp.status_code == 200

    async def test_if_none_match_and_redirect(self):
        async def get_response(req):
            resp = await client.get(req.path_info)
            resp["ETag"] = "spam"
            resp["Location"] = "/"
            resp.status_code = 301
            return resp

        self.req.META["HTTP_IF_NONE_MATCH"] = "spam"
        resp = await AsyncConditionalGetMiddleware(get_response)(self.req)
        assert resp.status_code == 301

    async def test_if_none_match_and_client_error(self):
        async def get_response(req):
            resp = await client.get(req.path_info)
            resp["ETag"] = "spam"
            resp.status_code = 400
            return resp

        self.req.META["HTTP_IF_NONE_MATCH"] = "spam"
        resp = await AsyncConditionalGetMiddleware(get_response)(self.req)
        assert resp.status_code == 400

    # Tests for the Last-Modified header

    async def test_if_modified_since_and_no_last_modified(self):
        self.req.META["HTTP_IF_MODIFIED_SINCE"] = "Sat, 12 Feb 2011 17:38:44 GMT"
        resp = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        assert resp.status_code == 200

    async def test_no_if_modified_since_and_last_modified(self):
        self.resp_headers["Last-Modified"] = "Sat, 12 Feb 2011 17:38:44 GMT"
        resp = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        assert resp.status_code == 200

    async def test_if_modified_since_and_same_last_modified(self):
        self.req.META["HTTP_IF_MODIFIED_SINCE"] = "Sat, 12 Feb 2011 17:38:44 GMT"
        self.resp_headers["Last-Modified"] = "Sat, 12 Feb 2011 17:38:44 GMT"
        self.resp = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        assert self.resp.status_code == 304

    async def test_if_modified_since_and_last_modified_in_the_past(self):
        self.req.META["HTTP_IF_MODIFIED_SINCE"] = "Sat, 12 Feb 2011 17:38:44 GMT"
        self.resp_headers["Last-Modified"] = "Sat, 12 Feb 2011 17:35:44 GMT"
        resp = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        assert resp.status_code == 304

    async def test_if_modified_since_and_last_modified_in_the_future(self):
        self.req.META["HTTP_IF_MODIFIED_SINCE"] = "Sat, 12 Feb 2011 17:38:44 GMT"
        self.resp_headers["Last-Modified"] = "Sat, 12 Feb 2011 17:41:44 GMT"
        self.resp = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        assert self.resp.status_code == 200

    async def test_if_modified_since_and_redirect(self):
        async def get_response(req):
            resp = await client.get(req.path_info)
            resp["Last-Modified"] = "Sat, 12 Feb 2011 17:35:44 GMT"
            resp["Location"] = "/"
            resp.status_code = 301
            return resp

        self.req.META["HTTP_IF_MODIFIED_SINCE"] = "Sat, 12 Feb 2011 17:38:44 GMT"
        resp = await AsyncConditionalGetMiddleware(get_response)(self.req)
        assert resp.status_code == 301

    async def test_if_modified_since_and_client_error(self):
        async def get_response(req):
            resp = await client.get(req.path_info)
            resp["Last-Modified"] = "Sat, 12 Feb 2011 17:35:44 GMT"
            resp.status_code = 400
            return resp

        self.req.META["HTTP_IF_MODIFIED_SINCE"] = "Sat, 12 Feb 2011 17:38:44 GMT"
        resp = await AsyncConditionalGetMiddleware(get_response)(self.req)
        assert resp.status_code == 400

    async def test_not_modified_headers(self):
        """
        The 304 Not Modified response should include only the headers required
        by RFC 9110 Section 15.4.5, Last-Modified, and the cookies.
        """

        async def get_response(req):
            resp = await client.get(req.path_info)
            resp["Date"] = "Sat, 12 Feb 2011 17:35:44 GMT"
            resp["Last-Modified"] = "Sat, 12 Feb 2011 17:35:44 GMT"
            resp["Expires"] = "Sun, 13 Feb 2011 17:35:44 GMT"
            resp["Vary"] = "Cookie"
            resp["Cache-Control"] = "public"
            resp["Content-Location"] = "/alt"
            resp["Content-Language"] = "en"  # shouldn't be preserved
            resp["ETag"] = '"spam"'
            resp.set_cookie("key", "value")
            return resp

        self.req.META["HTTP_IF_NONE_MATCH"] = '"spam"'

        new_response = await AsyncConditionalGetMiddleware(get_response)(self.req)
        assert new_response.status_code == 304
        base_response = await get_response(self.req)
        for header in (
            "Cache-Control",
            "Content-Location",
            "Date",
            "ETag",
            "Expires",
            "Last-Modified",
            "Vary",
        ):
            assert new_response.headers[header] == base_response.headers[header]
        assert new_response.cookies == base_response.cookies
        assert "Content-Language" not in new_response

    async def test_no_unsafe(self):
        """
        ConditionalGetMiddleware shouldn't return a conditional response on an
        unsafe request. A response has already been generated by the time
        ConditionalGetMiddleware is called, so it's too late to return a 412
        Precondition Failed.
        """

        async def get_200_response(req):
            return HttpResponse(status=200)

        response = await AsyncConditionalGetMiddleware(self.get_response)(self.req)
        etag = response.headers["ETag"]
        put_request = self.request_factory.put("/", headers={"if-match": etag})
        conditional_get_response = await AsyncConditionalGetMiddleware(
            get_200_response
        )(put_request)
        assert conditional_get_response.status_code == 200  # should never be a 412

    async def test_no_head(self):
        """
        ConditionalGetMiddleware shouldn't compute and return an ETag on a
        HEAD request since it can't do so accurately without access to the
        response body of the corresponding GET.
        """

        async def get_200_response(req):
            return HttpResponse(status=200)

        request = self.request_factory.head("/")
        conditional_get_response = await AsyncConditionalGetMiddleware(
            get_200_response
        )(request)
        assert "ETag" not in conditional_get_response
