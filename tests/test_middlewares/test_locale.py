import pytest


@pytest.mark.django_db
class TestLocaleMiddleware:
    @pytest.fixture(autouse=True)
    def set_settings(self, settings):
        settings.USE_I18N = True
        settings.LANGUAGES = [("en", "English"), ("fr", "French")]
        settings.MIDDLEWARE = [
            "django_async_extensions.middleware.locale.AsyncLocaleMiddleware",
            "django.middleware.common.CommonMiddleware",
        ]
        settings.ROOT_URLCONF = "test_middlewares.urls"

    async def test_streaming_response(self, async_client):
        # Regression test for #5241
        response = await async_client.get("/fr/streaming/")
        assert b"Oui/Non" in b"".join(
            [content async for content in response.streaming_content]
        )
        response = await async_client.get("/en/streaming/")
        assert b"Yes/No" in b"".join(
            [content async for content in response.streaming_content]
        )
