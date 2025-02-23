import datetime

import pytest

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.test import Client
from django.test.client import RequestFactory
from django.views.generic.detail import SingleObjectTemplateResponseMixin

from django_async_extensions.aviews.generic.base import AsyncView

from .models import Artist, Author, Book, Page


client = Client()


@pytest.fixture(autouse=True)
def url_setting_set(settings):
    old_root_urlconf = settings.ROOT_URLCONF
    settings.ROOT_URLCONF = "test_generic_views.urls"
    yield settings
    settings.ROOT_URLCONF = old_root_urlconf


@pytest.mark.django_db
class TestAsyncDetailView:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.artist1 = Artist.objects.create(name="Rene Magritte")
        self.author1 = Author.objects.create(
            name="Roberto Bolaño", slug="roberto-bolano"
        )
        self.author2 = Author.objects.create(
            name="Scott Rosenberg", slug="scott-rosenberg"
        )
        self.book1 = Book.objects.create(
            name="2066", slug="2066", pages=800, pubdate=datetime.date(2008, 10, 1)
        )
        self.book1.authors.add(self.author1)
        self.book2 = Book.objects.create(
            name="Dreaming in Code",
            slug="dreaming-in-code",
            pages=300,
            pubdate=datetime.date(2006, 5, 1),
        )
        self.page1 = Page.objects.create(
            content="I was once bitten by a moose.",
            template="test_generic_views/page_template.html",
        )

    def test_simple_object(self):
        res = client.get("/detail/obj/")
        assert res.status_code == 200
        assert res.context["object"] == {"foo": "bar"}
        assert isinstance(res.context["view"], AsyncView)
        assert res.template_name[0] == "test_generic_views/detail.html"

    def test_detail_by_pk(self):
        res = client.get(f"/detail/author/{self.author1.pk}/")
        assert res.status_code == 200
        assert res.context["object"] == self.author1
        assert res.context["author"] == self.author1
        assert res.template_name[0] == "test_generic_views/author_detail.html"

    def test_detail_missing_object(self):
        res = client.get("/detail/author/500/")
        assert res.status_code == 404

    def test_detail_object_does_not_exist(self):
        with pytest.raises(ObjectDoesNotExist):
            client.get("/detail/doesnotexist/1/")

    def test_detail_by_custom_pk(self):
        res = client.get(f"/detail/author/bycustompk/{self.author1.pk}/")
        assert res.status_code == 200
        assert res.context["object"] == self.author1
        assert res.context["author"] == self.author1
        assert res.template_name[0] == "test_generic_views/author_detail.html"

    def test_detail_by_slug(self):
        res = client.get("/detail/author/byslug/scott-rosenberg/")
        assert res.status_code == 200
        assert res.context["object"] == Author.objects.get(slug="scott-rosenberg")
        assert res.context["author"] == Author.objects.get(slug="scott-rosenberg")
        assert res.template_name[0] == "test_generic_views/author_detail.html"

    def test_detail_by_custom_slug(self):
        res = client.get("/detail/author/bycustomslug/scott-rosenberg/")
        assert res.status_code == 200
        assert res.context["object"] == Author.objects.get(slug="scott-rosenberg")
        assert res.context["author"] == Author.objects.get(slug="scott-rosenberg")
        assert res.template_name[0] == "test_generic_views/author_detail.html"

    def test_detail_by_pk_ignore_slug(self):
        res = client.get(
            f"/detail/author/bypkignoreslug/{self.author1.pk}-roberto-bolano/"
        )
        assert res.status_code == 200
        assert res.context["object"] == self.author1
        assert res.context["author"] == self.author1
        assert res.template_name[0] == "test_generic_views/author_detail.html"

    def test_detail_by_pk_ignore_slug_mismatch(self):
        res = client.get(
            f"/detail/author/bypkignoreslug/{self.author1.pk}-scott-rosenberg/"
        )
        assert res.status_code == 200
        assert res.context["object"] == self.author1
        assert res.context["author"] == self.author1
        assert res.template_name[0] == "test_generic_views/author_detail.html"

    def test_detail_by_pk_and_slug(self):
        res = client.get(
            f"/detail/author/bypkandslug/{self.author1.pk}-roberto-bolano/"
        )
        assert res.status_code == 200
        assert res.context["object"] == self.author1
        assert res.context["author"] == self.author1
        assert res.template_name[0] == "test_generic_views/author_detail.html"

    def test_detail_by_pk_and_slug_mismatch_404(self):
        res = client.get(
            f"/detail/author/bypkandslug/{self.author1.pk}-scott-rosenberg/"
        )
        assert res.status_code == 404

    def test_verbose_name(self):
        res = client.get(f"/detail/artist/{self.artist1.pk}/")
        assert res.status_code == 200
        assert res.context["object"] == self.artist1
        assert res.context["artist"] == self.artist1
        assert res.template_name[0] == "test_generic_views/artist_detail.html"

    def test_template_name(self):
        res = client.get(f"/detail/author/{self.author1.pk}/template_name/")
        assert res.status_code == 200
        assert res.context["object"] == self.author1
        assert res.context["author"] == self.author1
        assert res.template_name[0] == "test_generic_views/about.html"

    def test_template_name_suffix(self):
        res = client.get(f"/detail/author/{self.author1.pk}/template_name_suffix/")
        assert res.status_code == 200
        assert res.context["object"] == self.author1
        assert res.context["author"] == self.author1
        assert res.template_name[0] == "test_generic_views/author_view.html"

    def test_template_name_field(self):
        res = client.get(f"/detail/page/{self.page1.pk}/field/")
        assert res.status_code == 200
        assert res.context["object"] == self.page1
        assert res.context["page"] == self.page1
        assert res.template_name[0] == "test_generic_views/page_template.html"

    def test_context_object_name(self):
        res = client.get(f"/detail/author/{self.author1.pk}/context_object_name/")
        assert res.status_code == 200
        assert res.context["object"] == self.author1
        assert res.context["thingy"] == self.author1
        assert "author" not in res.context
        assert res.template_name[0] == "test_generic_views/author_detail.html"

    def test_duplicated_context_object_name(self):
        res = client.get(f"/detail/author/{self.author1.pk}/dupe_context_object_name/")
        assert res.status_code == 200
        assert res.context["object"] == self.author1
        assert "author" not in res.context
        assert res.template_name[0] == "test_generic_views/author_detail.html"

    def test_custom_detail(self):
        """
        AuthorCustomDetail overrides get() and ensures that
        SingleObjectMixin.get_context_object_name() always uses the obj
        parameter instead of self.object.
        """
        res = client.get(f"/detail/author/{self.author1.pk}/custom_detail/")
        assert res.status_code == 200
        assert res.context["custom_author"] == self.author1
        assert "author" not in res.context
        assert "object" not in res.context
        assert res.template_name[0] == "test_generic_views/author_detail.html"

    def test_deferred_queryset_template_name(self):
        class FormContext(SingleObjectTemplateResponseMixin):
            template_name = "test_generic_views/author_detail.html"
            request = RequestFactory().get("/")
            model = Author
            object = Author.objects.defer("name").get(pk=self.author1.pk)

        assert (
            FormContext().get_template_names()[0]
            == "test_generic_views/author_detail.html"
        )

    # def test_deferred_queryset_context_object_name(self):
    #     class FormContext(ModelFormMixin):
    #         request = RequestFactory().get("/")
    #         model = Author
    #         object = Author.objects.defer("name").get(pk=self.author1.pk)
    #         fields = ("name",)
    #
    #     form_context_data = FormContext().get_context_data()
    #     self.assertEqual(form_context_data["object"], self.author1)
    #     self.assertEqual(form_context_data["author"], self.author1)

    def test_invalid_url(self):
        with pytest.raises(AttributeError):
            client.get("/detail/author/invalid/url/")

    def test_invalid_queryset(self):
        msg = (
            "AuthorDetail is missing a QuerySet. Define AuthorDetail.model, "
            "AuthorDetail.queryset, or override AuthorDetail.get_queryset()."
        )
        with pytest.raises(ImproperlyConfigured, match=msg):
            client.get("/detail/author/invalid/qs/")

    def test_non_model_object_with_meta(self):
        res = client.get("/detail/nonmodel/1/")
        assert res.status_code == 200
        assert res.context["object"].id == "non_model_1"
