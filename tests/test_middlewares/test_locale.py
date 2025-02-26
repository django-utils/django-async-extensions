import pytest

from django.test import AsyncClient


client = AsyncClient()


@pytest.mark.django_db
class TestLocaleMiddleware:
    @pytest.fixture(autouse=True)
    def set_settings(self, settings):
        old_use_i18n = settings.USE_I18N
        old_language = settings.LANGUAGES
        old_middleware = settings.MIDDLEWARE
        old_urlconf = settings.ROOT_URLCONF

        settings.USE_I18N = True
        settings.LANGUAGES = [("en", "English"), ("fr", "French")]
        settings.MIDDLEWARE = [
            "django_async_extensions.amiddleware.locale.AsyncLocaleMiddleware",
            "django.middleware.common.CommonMiddleware",
        ]
        settings.ROOT_URLCONF = "test_middlewares.urls"

        yield settings

        settings.USE_I18N = old_use_i18n
        settings.LANGUAGES = old_language
        settings.MIDDLEWARE = old_middleware
        settings.ROOT_URLCONF = old_urlconf

    async def test_streaming_response(self):
        # Regression test for #5241
        response = await client.get("/fr/streaming/")
        assert b"Oui/Non" in b"".join(
            [content async for content in response.streaming_content]
        )
        response = await client.get("/en/streaming/")
        assert b"Yes/No" in b"".join(
            [content async for content in response.streaming_content]
        )
