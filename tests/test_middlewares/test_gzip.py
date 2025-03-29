import gzip
import random
import struct
from io import BytesIO

import pytest

from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.test import AsyncRequestFactory

from django_async_extensions.middleware.gzip import AsyncGZipMiddleware
from django_async_extensions.middleware.http import AsyncConditionalGetMiddleware

int2byte = struct.Struct(">B").pack


class TestGZipMiddleware:
    """
    Tests the GZipMiddleware.
    """

    short_string = b"This string is too short to be worth compressing."
    compressible_string = b"a" * 500
    incompressible_string = b"".join(
        int2byte(random.randint(0, 255)) for _ in range(500)  # noqa: S311
    )
    sequence = [b"a" * 500, b"b" * 200, b"a" * 300]
    sequence_unicode = ["a" * 500, "é" * 200, "a" * 300]
    request_factory = AsyncRequestFactory()

    @pytest.fixture(autouse=True)
    def setup(self):
        self.req = self.request_factory.get("/")
        self.req.META["HTTP_ACCEPT_ENCODING"] = "gzip, deflate"
        self.req.META["HTTP_USER_AGENT"] = (
            "Mozilla/5.0 (Windows NT 5.1; rv:9.0.1) Gecko/20100101 Firefox/9.0.1"
        )
        self.resp = HttpResponse()
        self.resp.status_code = 200
        self.resp.content = self.compressible_string
        self.resp["Content-Type"] = "text/html; charset=UTF-8"

    async def get_response(self, request):
        return self.resp

    @staticmethod
    def decompress(gzipped_string):
        with gzip.GzipFile(mode="rb", fileobj=BytesIO(gzipped_string)) as f:
            return f.read()

    @staticmethod
    def get_mtime(gzipped_string):
        with gzip.GzipFile(mode="rb", fileobj=BytesIO(gzipped_string)) as f:
            f.read()  # must read the data before accessing the header
            return f.mtime

    async def test_compress_response(self):
        """
        Compression is performed on responses with compressible content.
        """
        r = await AsyncGZipMiddleware(self.get_response)(self.req)
        assert self.decompress(r.content) == self.compressible_string
        assert r.get("Content-Encoding") == "gzip"
        assert r.get("Content-Length") == str(len(r.content))

    async def test_compress_streaming_response(self):
        """
        Compression is performed on responses with streaming content.
        """

        async def get_stream_response(request):
            resp = StreamingHttpResponse(self.sequence)
            resp["Content-Type"] = "text/html; charset=UTF-8"
            return resp

        r = await AsyncGZipMiddleware(get_stream_response)(self.req)
        assert self.decompress(b"".join(r)) == b"".join(self.sequence)
        assert r.get("Content-Encoding") == "gzip"
        assert r.has_header("Content-Length") is False

    async def test_compress_async_streaming_response(self):
        """
        Compression is performed on responses with async streaming content.
        """

        async def get_stream_response(request):
            async def iterator():
                for chunk in self.sequence:
                    yield chunk

            resp = StreamingHttpResponse(iterator())
            resp["Content-Type"] = "text/html; charset=UTF-8"
            return resp

        r = await AsyncGZipMiddleware(get_stream_response)(self.req)
        assert self.decompress(b"".join([chunk async for chunk in r])) == b"".join(
            self.sequence
        )
        assert r.get("Content-Encoding") == "gzip"
        assert r.has_header("Content-Length") is False

    async def test_compress_streaming_response_unicode(self):
        """
        Compression is performed on responses with streaming Unicode content.
        """

        async def get_stream_response_unicode(request):
            resp = StreamingHttpResponse(self.sequence_unicode)
            resp["Content-Type"] = "text/html; charset=UTF-8"
            return resp

        r = await AsyncGZipMiddleware(get_stream_response_unicode)(self.req)

        assert self.decompress(b"".join(r)) == b"".join(
            x.encode() for x in self.sequence_unicode
        )
        assert r.get("Content-Encoding") == "gzip"
        assert r.has_header("Content-Length") is False

    async def test_compress_file_response(self):
        """
        Compression is performed on FileResponse.
        """
        with open(__file__, "rb") as file1:

            async def get_response(req):
                file_resp = FileResponse(file1)
                file_resp["Content-Type"] = "text/html; charset=UTF-8"
                return file_resp

            r = await AsyncGZipMiddleware(get_response)(self.req)
            with open(__file__, "rb") as file2:
                assert self.decompress(b"".join(r)) == file2.read()
            assert r.get("Content-Encoding") == "gzip"
            assert r.file_to_stream is not file1

    async def test_compress_non_200_response(self):
        """
        Compression is performed on responses with a status other than 200
        (#10762).
        """
        self.resp.status_code = 404
        r = await AsyncGZipMiddleware(self.get_response)(self.req)
        assert self.decompress(r.content) == self.compressible_string
        assert r.get("Content-Encoding") == "gzip"

    async def test_no_compress_short_response(self):
        """
        Compression isn't performed on responses with short content.
        """
        self.resp.content = self.short_string
        r = await AsyncGZipMiddleware(self.get_response)(self.req)
        assert r.content == self.short_string
        assert r.get("Content-Encoding") is None

    async def test_no_compress_compressed_response(self):
        """
        Compression isn't performed on responses that are already compressed.
        """
        self.resp["Content-Encoding"] = "deflate"
        r = await AsyncGZipMiddleware(self.get_response)(self.req)
        assert r.content == self.compressible_string
        assert r.get("Content-Encoding") == "deflate"

    async def test_no_compress_incompressible_response(self):
        """
        Compression isn't performed on responses with incompressible content.
        """
        self.resp.content = self.incompressible_string
        r = await AsyncGZipMiddleware(self.get_response)(self.req)
        assert r.content == self.incompressible_string
        assert r.get("Content-Encoding") is None

    async def test_compress_deterministic(self):
        """
        Compression results are the same for the same content and don't
        include a modification time (since that would make the results
        of compression non-deterministic and prevent
        ConditionalGetMiddleware from recognizing conditional matches
        on gzipped content).
        """

        class DeterministicGZipMiddleware(AsyncGZipMiddleware):
            max_random_bytes = 0

        r1 = await DeterministicGZipMiddleware(self.get_response)(self.req)
        r2 = await DeterministicGZipMiddleware(self.get_response)(self.req)
        assert r1.content == r2.content
        assert self.get_mtime(r1.content) == 0
        assert self.get_mtime(r2.content) == 0

    async def test_random_bytes(self, mocker):
        """A random number of bytes is added to mitigate the BREACH attack."""
        mocker.patch(
            "django.utils.text.secrets.randbelow", autospec=True, return_value=3
        )
        r = await AsyncGZipMiddleware(self.get_response)(self.req)
        # The fourth byte of a gzip stream contains flags.
        assert r.content[3] == gzip.FNAME
        # A 3 byte filename "aaa" and a null byte are added.
        assert r.content[10:14] == b"aaa\x00"
        assert self.decompress(r.content) == self.compressible_string

    async def test_random_bytes_streaming_response(self, mocker):
        """A random number of bytes is added to mitigate the BREACH attack."""

        async def get_stream_response(request):
            resp = StreamingHttpResponse(self.sequence)
            resp["Content-Type"] = "text/html; charset=UTF-8"
            return resp

        mocker.patch(
            "django.utils.text.secrets.randbelow", autospec=True, return_value=3
        )
        r = await AsyncGZipMiddleware(get_stream_response)(self.req)
        content = b"".join(r)
        # The fourth byte of a gzip stream contains flags.
        assert content[3] == gzip.FNAME
        # A 3 byte filename "aaa" and a null byte are added.
        assert content[10:14] == b"aaa\x00"
        assert self.decompress(content) == b"".join(self.sequence)


class TestETagGZipMiddleware:
    """
    ETags are handled properly by GZipMiddleware.
    """

    rf = AsyncRequestFactory()
    compressible_string = b"a" * 500

    async def test_strong_etag_modified(self):
        """
        GZipMiddleware makes a strong ETag weak.
        """

        async def get_response(req):
            response = HttpResponse(self.compressible_string)
            response.headers["ETag"] = '"eggs"'
            return response

        request = self.rf.get("/", headers={"accept-encoding": "gzip, deflate"})
        gzip_response = await AsyncGZipMiddleware(get_response)(request)
        assert gzip_response.headers["ETag"] == 'W/"eggs"'

    async def test_weak_etag_not_modified(self):
        """
        GZipMiddleware doesn't modify a weak ETag.
        """

        async def get_response(req):
            response = HttpResponse(self.compressible_string)
            response.headers["ETag"] = 'W/"eggs"'
            return response

        request = self.rf.get("/", headers={"accept-encoding": "gzip, deflate"})
        gzip_response = await AsyncGZipMiddleware(get_response)(request)
        assert gzip_response.headers["ETag"] == 'W/"eggs"'

    async def test_etag_match(self):
        """
        GZipMiddleware allows 304 Not Modified responses.
        """

        async def get_response(req):
            return HttpResponse(self.compressible_string)

        async def get_cond_response(req):
            return await AsyncConditionalGetMiddleware(get_response)(req)

        request = self.rf.get("/", headers={"accept-encoding": "gzip, deflate"})
        response = await AsyncGZipMiddleware(get_cond_response)(request)
        gzip_etag = response.headers["ETag"]
        next_request = self.rf.get(
            "/",
            headers={"accept-encoding": "gzip, deflate", "if-none-match": gzip_etag},
        )
        next_response = await AsyncConditionalGetMiddleware(get_response)(next_request)
        assert next_response.status_code == 304
