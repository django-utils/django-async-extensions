from django import forms
from django.conf import settings
from django.test import Client, AsyncClient
from django.test.client import RequestFactory

import pytest

from django_async_extensions.aviews.generic.edit import (
    AsyncFormMixin,
    AsyncModelFormMixin,
)

from . import views
from .models import Author


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
