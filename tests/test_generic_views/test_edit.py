import re

from django import forms
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, AsyncClient
from django.test.client import RequestFactory

import pytest
from django.urls import reverse
from pytest_django.asserts import assertRedirects, assertQuerySetEqual

from django_async_extensions.aviews.generic import AsyncView
from django_async_extensions.aviews.generic.edit import (
    AsyncFormMixin,
    AsyncModelFormMixin,
    AsyncCreateView,
)

from . import views
from .models import Author, Artist
from .forms import AuthorForm

client = Client()
aclient = AsyncClient()


class TestFormMixin:
    request_factory = RequestFactory()

    def test_initial_data(self):
        """Test instance independence of initial data dict (see #16138)"""
        initial_1 = AsyncFormMixin().get_initial()
        initial_1["foo"] = "bar"
        initial_2 = AsyncFormMixin().get_initial()
        assert initial_1 != initial_2

    def test_get_prefix(self):
        """Test prefix can be set (see #18872)"""
        test_string = "test"

        get_request = self.request_factory.get("/")

        class TestFormMixinInner(AsyncFormMixin):
            request = get_request

        default_kwargs = TestFormMixinInner().get_form_kwargs()
        assert default_kwargs.get("prefix") is None

        set_mixin = TestFormMixinInner()
        set_mixin.prefix = test_string
        set_kwargs = set_mixin.get_form_kwargs()
        assert test_string == set_kwargs.get("prefix")

    async def test_get_form(self):
        class TestFormMixinInner(AsyncFormMixin):
            request = self.request_factory.get("/")

        assert isinstance(
            await TestFormMixinInner().get_form(forms.Form), forms.Form
        ), "get_form() should use provided form class."

        class FormClassTestFormMixin(TestFormMixinInner):
            form_class = forms.Form

        assert isinstance(
            await FormClassTestFormMixin().get_form(), forms.Form
        ), "get_form() should fallback to get_form_class() if none is provided."

    async def test_get_context_data(self):
        class FormContext(AsyncFormMixin):
            request = self.request_factory.get("/")
            form_class = forms.Form

        context_data = await FormContext().get_context_data()
        assert isinstance(context_data["form"], forms.Form)


@pytest.mark.django_db
class TestBasicForm:
    @pytest.fixture(autouse=True)
    def urlconf_for_tests(self):
        settings.ROOT_URLCONF = "test_generic_views.urls"

    # def test_post_data(self):
    #     res = client.post("/contact/", {"name": "Me", "message": "Hello"})
    #     assertRedirects(res, "/list/authors/")

    async def test_late_form_validation(self):
        """
        A form can be marked invalid in the form_valid() method (#25548).
        """
        res = await aclient.post(
            "/late-validation/", {"name": "Me", "message": "Hello"}
        )
        assert res.context["form"].is_valid() is False


class TestModelFormMixin:
    async def test_get_form(self):
        form_class = await views.AuthorGetQuerySetFormView().get_form_class()
        assert form_class._meta.model == Author

    def test_get_form_checks_for_object(self):
        mixin = AsyncModelFormMixin()
        mixin.request = RequestFactory().get("/")
        assert {"initial": {}, "prefix": None} == mixin.get_form_kwargs()


@pytest.mark.django_db
class TestCreateView:
    @pytest.fixture(autouse=True)
    def urlconf_for_tests(self):
        settings.ROOT_URLCONF = "test_generic_views.urls"

    def test_create(self):
        res = client.get("/edit/authors/create/")
        assert res.status_code == 200
        assert isinstance(res.context["form"], forms.ModelForm)
        assert isinstance(res.context["view"], AsyncView)
        assert "object" not in res.context
        assert "author" not in res.context
        assert res.template_name[0] == "test_generic_views/author_form.html"

        res = client.post(
            "/edit/authors/create/",
            {"name": "Randall Munroe", "slug": "randall-munroe"},
        )
        assert res.status_code == 302
        assertRedirects(res, "/list/authors/")
        assertQuerySetEqual(
            Author.objects.values_list("name", flat=True), ["Randall Munroe"]
        )

    def test_create_invalid(self):
        res = client.post(
            "/edit/authors/create/", {"name": "A" * 101, "slug": "randall-munroe"}
        )
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/author_form.html"
        assert len(res.context["form"].errors) == 1
        assert Author.objects.count() == 0

    def test_create_with_object_url(self):
        res = client.post("/edit/artists/create/", {"name": "Rene Magritte"})
        assert res.status_code == 302
        artist = Artist.objects.get(name="Rene Magritte")
        assertRedirects(res, "/detail/artist/%d/" % artist.pk)
        assertQuerySetEqual(Artist.objects.all(), [artist])

    def test_create_with_redirect(self):
        res = client.post(
            "/edit/authors/create/redirect/",
            {"name": "Randall Munroe", "slug": "randall-munroe"},
        )
        assert res.status_code == 302
        assertRedirects(res, "/edit/authors/create/")
        assertQuerySetEqual(
            Author.objects.values_list("name", flat=True), ["Randall Munroe"]
        )

    def test_create_with_interpolated_redirect(self):
        res = client.post(
            "/edit/authors/create/interpolate_redirect/",
            {"name": "Randall Munroe", "slug": "randall-munroe"},
        )
        assertQuerySetEqual(
            Author.objects.values_list("name", flat=True), ["Randall Munroe"]
        )
        assert res.status_code == 302
        pk = Author.objects.first().pk
        assertRedirects(res, "/edit/author/%d/update/" % pk)
        # Also test with escaped chars in URL
        res = client.post(
            "/edit/authors/create/interpolate_redirect_nonascii/",
            {"name": "John Doe", "slug": "john-doe"},
        )
        assert res.status_code == 302
        pk = Author.objects.get(name="John Doe").pk
        assertRedirects(res, "/%C3%A9dit/author/{}/update/".format(pk))

    def test_create_with_special_properties(self):
        res = client.get("/edit/authors/create/special/")
        assert res.status_code == 200
        assert isinstance(res.context["form"], views.AuthorForm)
        assert "object" not in res.context
        assert "author" not in res.context
        assert res.template_name[0] == "test_generic_views/form.html"

        res = client.post(
            "/edit/authors/create/special/",
            {"name": "Randall Munroe", "slug": "randall-munroe"},
        )
        assert res.status_code == 302
        obj = Author.objects.get(slug="randall-munroe")
        assertRedirects(res, reverse("author_detail", kwargs={"pk": obj.pk}))
        assertQuerySetEqual(Author.objects.all(), [obj])

    def test_create_without_redirect(self):
        msg = (
            "No URL to redirect to.  Either provide a url or define a "
            "get_absolute_url method on the Model."
        )
        with pytest.raises(ImproperlyConfigured, match=msg):
            client.post(
                "/edit/authors/create/naive/",
                {"name": "Randall Munroe", "slug": "randall-munroe"},
            )

    def test_create_restricted(self):
        res = client.post(
            "/edit/authors/create/restricted/",
            {"name": "Randall Munroe", "slug": "randall-munroe"},
        )
        assert res.status_code == 302
        assertRedirects(res, "/accounts/login/?next=/edit/authors/create/restricted/")

    async def test_create_view_with_restricted_fields(self):
        class MyCreateView(AsyncCreateView):
            model = Author
            fields = ["name"]

        form_class = await MyCreateView().get_form_class()
        assert list(form_class.base_fields) == ["name"]

    async def test_create_view_all_fields(self):
        class MyCreateView(AsyncCreateView):
            model = Author
            fields = "__all__"

        form_class = await MyCreateView().get_form_class()
        assert list(form_class.base_fields) == ["name", "slug"]

    async def test_create_view_without_explicit_fields(self):
        class MyCreateView(AsyncCreateView):
            model = Author

        message = re.escape(
            "Using ModelFormMixin (base class of MyCreateView) without the "
            "'fields' attribute is prohibited."
        )
        with pytest.raises(ImproperlyConfigured, match=message):
            await MyCreateView().get_form_class()

    async def test_define_both_fields_and_form_class(self):
        class MyCreateView(AsyncCreateView):
            model = Author
            form_class = AuthorForm
            fields = ["name"]

        message = "Specifying both 'fields' and 'form_class' is not permitted."
        with pytest.raises(ImproperlyConfigured, match=message):
            await MyCreateView().get_form_class()


@pytest.mark.django_db
class TestUpdateView:
    @pytest.fixture(autouse=True)
    def urlconf_for_tests(self):
        settings.ROOT_URLCONF = "test_generic_views.urls"

    @pytest.fixture(autouse=True)
    def setup(cls):
        cls.author = Author.objects.create(
            pk=1,  # Required for OneAuthorUpdate.
            name="Randall Munroe",
            slug="randall-munroe",
        )

    def test_update_post(self):
        res = client.get("/edit/author/%d/update/" % self.author.pk)
        assert res.status_code == 200
        assert isinstance(res.context["form"], forms.ModelForm)
        assert res.context["object"] == self.author
        assert res.context["author"] == self.author
        assert res.template_name[0] == "test_generic_views/author_form.html"
        assert res.context["view"].get_form_called_count == 1

        # Modification with both POST and PUT (browser compatible)
        res = client.post(
            "/edit/author/%d/update/" % self.author.pk,
            {"name": "Randall Munroe (xkcd)", "slug": "randall-munroe"},
        )
        assert res.status_code == 302
        assertRedirects(res, "/list/authors/")
        assertQuerySetEqual(
            Author.objects.values_list("name", flat=True), ["Randall Munroe (xkcd)"]
        )

    def test_update_invalid(self):
        res = client.post(
            "/edit/author/%d/update/" % self.author.pk,
            {"name": "A" * 101, "slug": "randall-munroe"},
        )
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/author_form.html"
        assert len(res.context["form"].errors) == 1
        assertQuerySetEqual(Author.objects.all(), [self.author])
        assert res.context["view"].get_form_called_count == 1

    def test_update_with_object_url(self):
        a = Artist.objects.create(name="Rene Magritte")
        res = client.post("/edit/artists/%d/update/" % a.pk, {"name": "Rene Magritte"})
        assert res.status_code == 302
        assertRedirects(res, "/detail/artist/%d/" % a.pk)
        assertQuerySetEqual(Artist.objects.all(), [a])

    def test_update_with_redirect(self):
        res = client.post(
            "/edit/author/%d/update/redirect/" % self.author.pk,
            {"name": "Randall Munroe (author of xkcd)", "slug": "randall-munroe"},
        )
        assert res.status_code == 302
        assertRedirects(res, "/edit/authors/create/")
        assertQuerySetEqual(
            Author.objects.values_list("name", flat=True),
            ["Randall Munroe (author of xkcd)"],
        )

    def test_update_with_interpolated_redirect(self):
        res = client.post(
            "/edit/author/%d/update/interpolate_redirect/" % self.author.pk,
            {"name": "Randall Munroe (author of xkcd)", "slug": "randall-munroe"},
        )
        assertQuerySetEqual(
            Author.objects.values_list("name", flat=True),
            ["Randall Munroe (author of xkcd)"],
        )
        assert res.status_code == 302
        pk = Author.objects.first().pk
        assertRedirects(res, "/edit/author/%d/update/" % pk)
        # Also test with escaped chars in URL
        res = client.post(
            "/edit/author/%d/update/interpolate_redirect_nonascii/" % self.author.pk,
            {"name": "John Doe", "slug": "john-doe"},
        )
        assert res.status_code == 302
        pk = Author.objects.get(name="John Doe").pk
        assertRedirects(res, "/%C3%A9dit/author/{}/update/".format(pk))

    def test_update_with_special_properties(self):
        res = client.get("/edit/author/%d/update/special/" % self.author.pk)
        assert res.status_code == 200
        assert isinstance(res.context["form"], views.AuthorForm)
        assert res.context["object"] == self.author
        assert res.context["thingy"] == self.author
        assert "author" not in res.context
        assert res.template_name[0] == "test_generic_views/form.html"

        res = client.post(
            "/edit/author/%d/update/special/" % self.author.pk,
            {"name": "Randall Munroe (author of xkcd)", "slug": "randall-munroe"},
        )
        assert res.status_code == 302
        assertRedirects(res, "/detail/author/%d/" % self.author.pk)
        assertQuerySetEqual(
            Author.objects.values_list("name", flat=True),
            ["Randall Munroe (author of xkcd)"],
        )

    def test_update_without_redirect(self):
        msg = (
            "No URL to redirect to.  Either provide a url or define a "
            "get_absolute_url method on the Model."
        )
        with pytest.raises(ImproperlyConfigured, match=msg):
            client.post(
                "/edit/author/%d/update/naive/" % self.author.pk,
                {"name": "Randall Munroe (author of xkcd)", "slug": "randall-munroe"},
            )

    def test_update_get_object(self):
        res = client.get("/edit/author/update/")
        assert res.status_code == 200
        assert isinstance(res.context["form"], forms.ModelForm)
        assert isinstance(res.context["view"], AsyncView)
        assert res.context["object"] == self.author
        assert res.context["author"] == self.author
        assert res.template_name[0] == "test_generic_views/author_form.html"

        # Modification with both POST and PUT (browser compatible)
        res = client.post(
            "/edit/author/update/",
            {"name": "Randall Munroe (xkcd)", "slug": "randall-munroe"},
        )
        assert res.status_code == 302
        assertRedirects(res, "/list/authors/")
        assertQuerySetEqual(
            Author.objects.values_list("name", flat=True), ["Randall Munroe (xkcd)"]
        )


@pytest.mark.django_db
class TestDeleteView:
    @pytest.fixture(autouse=True)
    def urlconf_for_tests(self):
        settings.ROOT_URLCONF = "test_generic_views.urls"

    @pytest.fixture(autouse=True)
    def setup(cls):
        cls.author = Author.objects.create(
            name="Randall Munroe",
            slug="randall-munroe",
        )

    def test_delete_by_post(self):
        res = client.get("/edit/author/%d/delete/" % self.author.pk)
        assert res.status_code == 200
        assert res.context["object"] == self.author
        assert res.context["author"] == self.author
        assert res.template_name[0] == "test_generic_views/author_confirm_delete.html"

        # Deletion with POST
        res = client.post("/edit/author/%d/delete/" % self.author.pk)
        assert res.status_code == 302
        assertRedirects(res, "/list/authors/")
        assertQuerySetEqual(Author.objects.all(), [])

    def test_delete_by_delete(self):
        # Deletion with browser compatible DELETE method
        res = client.delete("/edit/author/%d/delete/" % self.author.pk)
        assert res.status_code == 302
        assertRedirects(res, "/list/authors/")
        assertQuerySetEqual(Author.objects.all(), [])

    def test_delete_with_redirect(self):
        res = client.post("/edit/author/%d/delete/redirect/" % self.author.pk)
        assert res.status_code == 302
        assertRedirects(res, "/edit/authors/create/")
        assertQuerySetEqual(Author.objects.all(), [])

    def test_delete_with_interpolated_redirect(self):
        res = client.post(
            "/edit/author/%d/delete/interpolate_redirect/" % self.author.pk
        )
        assert res.status_code == 302
        assertRedirects(res, "/edit/authors/create/?deleted=%d" % self.author.pk)
        assertQuerySetEqual(Author.objects.all(), [])
        # Also test with escaped chars in URL
        a = Author.objects.create(
            **{"name": "Randall Munroe", "slug": "randall-munroe"}
        )
        res = client.post(
            "/edit/author/{}/delete/interpolate_redirect_nonascii/".format(a.pk)
        )
        assert res.status_code == 302
        assertRedirects(res, "/%C3%A9dit/authors/create/?deleted={}".format(a.pk))

    def test_delete_with_special_properties(self):
        res = client.get("/edit/author/%d/delete/special/" % self.author.pk)
        assert res.status_code == 200
        assert res.context["object"] == self.author
        assert res.context["thingy"] == self.author
        assert "author" not in res.context
        assert res.template_name[0] == "test_generic_views/confirm_delete.html"

        res = client.post("/edit/author/%d/delete/special/" % self.author.pk)
        assert res.status_code == 302
        assertRedirects(res, "/list/authors/")
        assertQuerySetEqual(Author.objects.all(), [])

    def test_delete_without_redirect(self):
        msg = "No URL to redirect to. Provide a success_url."
        with pytest.raises(ImproperlyConfigured, match=msg):
            client.post("/edit/author/%d/delete/naive/" % self.author.pk)

    def test_delete_with_form_as_post(self):
        res = client.get("/edit/author/%d/delete/form/" % self.author.pk)
        assert res.status_code == 200
        assert res.context["object"] == self.author
        assert res.context["author"] == self.author
        assert res.template_name[0] == "test_generic_views/author_confirm_delete.html"
        res = client.post(
            "/edit/author/%d/delete/form/" % self.author.pk, data={"confirm": True}
        )
        assert res.status_code == 302
        assertRedirects(res, "/list/authors/")
        assert list(Author.objects.all()) == []

    def test_delete_with_form_as_post_with_validation_error(self):
        res = client.get("/edit/author/%d/delete/form/" % self.author.pk)
        assert res.status_code == 200
        assert res.context["object"] == self.author
        assert res.context["author"] == self.author
        assert res.template_name[0] == "test_generic_views/author_confirm_delete.html"

        res = client.post("/edit/author/%d/delete/form/" % self.author.pk)
        assert res.status_code == 200
        assert len(res.context_data["form"].errors) == 2
        assert res.context_data["form"].errors["__all__"] == [
            "You must confirm the delete."
        ]
        assert res.context_data["form"].errors["confirm"] == ["This field is required."]
