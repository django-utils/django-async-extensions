import pytest

from asgiref.sync import sync_to_async

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import translation

from django_async_extensions.acontrib.flatpages.forms import AsyncFlatpageForm
from django_async_extensions.acontrib.flatpages.models import AsyncFlatPage


@pytest.mark.django_db(transaction=True)
class TestFlatpageAdminForm:
    @pytest.fixture(autouse=True)
    def set_settings(self):
        old_installed_apps = settings.INSTALLED_APPS
        old_site_id = settings.SITE_ID

        settings.INSTALLED_APPS.append("django_async_extensions.acontrib.flatpages")
        settings.SITE_ID = 1

        yield

        settings.INSTALLED_APPS = old_installed_apps
        settings.SITE_ID = old_site_id

    @pytest.fixture(autouse=True)
    def setup(self):
        # don't use the manager because we want to ensure the site exists
        # with pk=1, regardless of whether or not it already exists.
        self.site1 = Site(pk=1, domain="example.com", name="example.com")
        self.site1.save()

        # Site fields cache needs to be cleared after flatpages is added to
        # INSTALLED_APPS
        Site._meta._expire_cache()
        self.form_data = {
            "title": "A test page",
            "content": "This is a test",
            "sites": [settings.SITE_ID],
        }

    def test_flatpage_admin_form_url_validation(self):
        "The flatpage admin form correctly validates urls"
        assert AsyncFlatpageForm(
            data=dict(url="/new_flatpage/", **self.form_data)
        ).is_valid()
        assert AsyncFlatpageForm(
            data=dict(url="/some.special~chars/", **self.form_data)
        ).is_valid()
        assert AsyncFlatpageForm(
            data=dict(url="/some.very_special~chars-here/", **self.form_data)
        ).is_valid()

        assert (
            AsyncFlatpageForm(data=dict(url="/a space/", **self.form_data)).is_valid()
            is False
        )
        assert (
            AsyncFlatpageForm(data=dict(url="/a % char/", **self.form_data)).is_valid()
            is False
        )
        assert (
            AsyncFlatpageForm(data=dict(url="/a ! char/", **self.form_data)).is_valid()
            is False
        )
        assert (
            AsyncFlatpageForm(data=dict(url="/a & char/", **self.form_data)).is_valid()
            is False
        )
        assert (
            AsyncFlatpageForm(data=dict(url="/a ? char/", **self.form_data)).is_valid()
            is False
        )

    def test_flatpage_requires_leading_slash(self):
        form = AsyncFlatpageForm(data=dict(url="no_leading_slash/", **self.form_data))
        with translation.override("en"):
            assert form.is_valid() is False
            assert form.errors["url"] == ["URL is missing a leading slash."]

    @pytest.fixture()
    def common_fixture(self, settings):
        old_middleware = settings.MIDDLEWARE
        settings.MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]

        yield
        settings.MIDDLEWARE = old_middleware

    @pytest.fixture()
    def append_True_fixture(self, settings):
        old_append_slash = settings.APPEND_SLASH
        settings.APPEND_SLASH = True
        yield
        settings.APPEND_SLASH = old_append_slash

    def test_flatpage_requires_trailing_slash_with_append_slash(
        self, common_fixture, append_True_fixture
    ):
        form = AsyncFlatpageForm(data=dict(url="/no_trailing_slash", **self.form_data))
        with translation.override("en"):
            assert (
                form.fields["url"].help_text
                == "Example: “/about/contact/”. Make sure to have leading and "
                "trailing slashes."
            )
            assert form.is_valid() is False
            assert form.errors["url"] == ["URL is missing a trailing slash."]

    @pytest.fixture()
    def append_False_fixture(self, settings):
        old_append_slash = settings.APPEND_SLASH
        settings.APPEND_SLASH = False
        yield
        settings.APPEND_SLASH = old_append_slash

    async def test_flatpage_doesnt_requires_trailing_slash_without_append_slash(
        self, common_fixture, append_False_fixture
    ):
        form = await sync_to_async(AsyncFlatpageForm)(
            data=dict(url="/no_trailing_slash", **self.form_data)
        )
        assert await sync_to_async(form.is_valid)()
        with translation.override("en"):
            assert (
                form.fields["url"].help_text
                == "Example: “/about/contact”. Make sure to have a leading slash."
            )

    def test_flatpage_admin_form_url_uniqueness_validation(self):
        """
        The flatpage admin form correctly enforces url uniqueness among
        flatpages of the same site.
        """
        data = dict(url="/myflatpage1/", **self.form_data)

        AsyncFlatpageForm(data=data).save()

        f = AsyncFlatpageForm(data=data)

        with translation.override("en"):
            assert f.is_valid() is False

            assert f.errors == {
                "__all__": [
                    "Flatpage with url /myflatpage1/ already exists for site "
                    "example.com"
                ]
            }

    def test_flatpage_admin_form_edit(self):
        """
        Existing flatpages can be edited in the admin form without triggering
        the url-uniqueness validation.
        """
        existing = AsyncFlatPage.objects.create(
            url="/myflatpage1/", title="Some page", content="The content"
        )
        existing.sites.add(settings.SITE_ID)

        data = dict(url="/myflatpage1/", **self.form_data)

        f = AsyncFlatpageForm(data=data, instance=existing)

        assert f.is_valid(), f.errors

        updated = f.save()

        assert updated.title == "A test page"

    def test_flatpage_nosites(self):
        data = dict(url="/myflatpage1/", **self.form_data)
        data.update({"sites": ""})

        f = AsyncFlatpageForm(data=data)

        assert f.is_valid() is False

        assert f.errors == {"sites": [translation.gettext("This field is required.")]}
