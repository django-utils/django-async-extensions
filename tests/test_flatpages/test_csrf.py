import pytest
from asgiref.sync import sync_to_async

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import AsyncClient

from django_async_extensions.acontrib.flatpages.models import AsyncFlatPage


@pytest.mark.django_db(transaction=True)
class TestFlatpageCSRF:
    @pytest.fixture(autouse=True)
    def set_settings(self):
        old_installed_apps = settings.INSTALLED_APPS
        old_middleware = settings.MIDDLEWARE
        old_root_urlconf = settings.ROOT_URLCONF
        old_csrf_failure_view = settings.CSRF_FAILURE_VIEW
        old_site_id = settings.SITE_ID

        settings.INSTALLED_APPS.append("django_async_extensions.acontrib.flatpages")
        settings.MIDDLEWARE = [
            "django.middleware.common.CommonMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django_async_extensions.acontrib.flatpages.middleware.AsyncFlatpageFallbackMiddleware",
        ]
        settings.ROOT_URLCONF = "test_flatpages.urls"
        settings.CSRF_FAILURE_VIEW = "django.views.csrf.csrf_failure"
        settings.SITE_ID = 1

        yield settings

        settings.INSTALLED_APPS = old_installed_apps
        settings.MIDDLEWARE = old_middleware
        settings.ROOT_URLCONF = old_root_urlconf
        settings.CSRF_FAILURE_VIEW = old_csrf_failure_view
        settings.SITE_ID = old_site_id

    @pytest.fixture(autouse=True)
    def setup(self):
        # don't use the manager because we want to ensure the site exists
        # with pk=1, regardless of whether or not it already exists.
        self.site1 = Site(pk=1, domain="example.com", name="example.com")
        self.site1.save()
        self.fp1 = AsyncFlatPage.objects.create(
            url="/flatpage/",
            title="A Flatpage",
            content="Isn't it flat!",
            enable_comments=False,
            template_name="",
            registration_required=False,
        )
        self.fp2 = AsyncFlatPage.objects.create(
            url="/location/flatpage/",
            title="A Nested Flatpage",
            content="Isn't it flat and deep!",
            enable_comments=False,
            template_name="",
            registration_required=False,
        )
        self.fp3 = AsyncFlatPage.objects.create(
            url="/sekrit/",
            title="Sekrit Flatpage",
            content="Isn't it sekrit!",
            enable_comments=False,
            template_name="",
            registration_required=True,
        )
        self.fp4 = AsyncFlatPage.objects.create(
            url="/location/sekrit/",
            title="Sekrit Nested Flatpage",
            content="Isn't it sekrit and deep!",
            enable_comments=False,
            template_name="",
            registration_required=True,
        )
        self.fp1.sites.add(self.site1)
        self.fp2.sites.add(self.site1)
        self.fp3.sites.add(self.site1)
        self.fp4.sites.add(self.site1)

        self.client = AsyncClient(enforce_csrf_checks=True)

    async def test_view_flatpage(self):
        "A flatpage can be served through a view, even when the middleware is in use"
        response = await self.client.get("/flatpage_root/flatpage/")
        assert b"<p>Isn't it flat!</p>" in response.content

    async def test_view_non_existent_flatpage(self):
        """
        A nonexistent flatpage raises 404 when served through a view, even when
        the middleware is in use.
        """
        response = await self.client.get("/flatpage_root/no_such_flatpage/")
        assert response.status_code == 404

    async def test_view_authenticated_flatpage(self):
        "A flatpage served through a view can require authentication"
        response = await self.client.get("/flatpage_root/sekrit/")
        assert response.status_code == 302
        assert response.url == "/accounts/login/?next=/flatpage_root/sekrit/"
        user = await sync_to_async(User.objects.create_user)(
            "testuser", "test@example.com", "s3krit"
        )
        await self.client.aforce_login(user)
        response = await self.client.get("/flatpage_root/sekrit/")
        assert b"<p>Isn't it sekrit!</p>" in response.content

    async def test_fallback_flatpage(self):
        "A flatpage can be served by the fallback middleware"
        response = await self.client.get("/flatpage/")
        assert b"<p>Isn't it flat!</p>" in response.content

    async def test_fallback_non_existent_flatpage(self):
        """
        A nonexistent flatpage raises a 404 when served by the fallback
        middleware.
        """
        response = await self.client.get("/no_such_flatpage/")
        assert response.status_code == 404

    async def test_post_view_flatpage(self):
        """
        POSTing to a flatpage served through a view will raise a CSRF error if
        no token is provided.
        """
        response = await self.client.post("/flatpage_root/flatpage/")
        assert response.status_code == 403

    async def test_post_fallback_flatpage(self):
        """
        POSTing to a flatpage served by the middleware will raise a CSRF error
        if no token is provided.
        """
        response = await self.client.post("/flatpage/")
        assert response.status_code == 403

    async def test_post_unknown_page(self):
        "POSTing to an unknown page isn't caught as a 403 CSRF error"
        response = await self.client.post("/no_such_page/")
        assert response.status_code == 404
