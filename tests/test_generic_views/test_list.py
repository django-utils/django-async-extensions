import datetime
import re

import pytest

from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase

from django_async_extensions.aviews.generic.base import AsyncView

from .models import Artist, Author, Book, Page

client = Client()


@pytest.fixture(autouse=True)
def url_setting_set(settings):
    old_root_urlconf = settings.ROOT_URLCONF
    settings.ROOT_URLCONF = "test_generic_views.urls"
    yield settings
    settings.ROOT_URLCONF = old_root_urlconf


@pytest.mark.django_db(transaction=True)
class ListViewTests(TestCase):
    @classmethod
    def setUpTestData(self):
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
            template="generic_views/page_template.html",
        )

    def test_items(self):
        res = client.get("/list/dict/")
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/list.html"
        assert res.context["object_list"][0]["first"] == "John"

    def test_queryset(self):
        res = client.get("/list/authors/")
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/author_list.html"
        assert list(res.context["object_list"]) == list(Author.objects.all())
        assert isinstance(res.context["view"], AsyncView)
        assert res.context["author_list"] is res.context["object_list"]
        assert res.context["paginator"] is None
        assert res.context["page_obj"] is None
        assert res.context["is_paginated"] is False

    def test_paginated_queryset(self):
        self._make_authors(100)
        res = client.get("/list/authors/paginated/")
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/author_list.html"
        assert len(res.context["object_list"]) == 30
        assert res.context["author_list"] is res.context["object_list"]
        assert res.context["is_paginated"]
        assert res.context["page_obj"].number == 1
        assert res.context["paginator"].num_pages == 4
        assert res.context["author_list"][0].name == "Author 00"
        assert list(res.context["author_list"])[-1].name == "Author 29"

    def test_paginated_queryset_shortdata(self):
        # Short datasets also result in a paginated view.
        res = client.get("/list/authors/paginated/")
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/author_list.html"
        assert list(res.context["object_list"]) == list(Author.objects.all())
        assert res.context["author_list"] is res.context["object_list"]
        assert res.context["page_obj"].number == 1
        assert res.context["paginator"].num_pages == 1
        assert res.context["is_paginated"] is False

    def test_paginated_get_page_by_query_string(self):
        self._make_authors(100)
        res = client.get("/list/authors/paginated/", {"page": "2"})
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/author_list.html"
        assert len(res.context["object_list"]) == 30
        assert res.context["author_list"] is res.context["object_list"]
        assert res.context["author_list"][0].name == "Author 30"
        assert res.context["page_obj"].number == 2

    def test_paginated_get_last_page_by_query_string(self):
        self._make_authors(100)
        res = client.get("/list/authors/paginated/", {"page": "last"})
        assert res.status_code == 200
        assert len(res.context["object_list"]) == 10
        assert res.context["author_list"] is res.context["object_list"]
        assert res.context["author_list"][0].name == "Author 90"
        assert res.context["page_obj"].number == 4

    def test_paginated_get_page_by_urlvar(self):
        self._make_authors(100)
        res = client.get("/list/authors/paginated/3/")
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/author_list.html"
        assert len(res.context["object_list"]) == 30
        assert res.context["author_list"] is res.context["object_list"]
        assert res.context["author_list"][0].name == "Author 60"
        assert res.context["page_obj"].number == 3

    def test_paginated_page_out_of_range(self):
        self._make_authors(100)
        res = client.get("/list/authors/paginated/42/")
        assert res.status_code == 404

    def test_paginated_invalid_page(self):
        self._make_authors(100)
        res = client.get("/list/authors/paginated/?page=frog")
        assert res.status_code == 404

    def test_paginated_custom_paginator_class(self):
        self._make_authors(7)
        res = client.get("/list/authors/paginated/custom_class/")
        assert res.status_code == 200
        assert res.context["paginator"].num_pages == 1
        # Custom pagination allows for 2 orphans on a page size of 5
        assert len(res.context["object_list"]) == 7

    def test_paginated_custom_page_kwarg(self):
        self._make_authors(100)
        res = client.get("/list/authors/paginated/custom_page_kwarg/", {"pagina": "2"})
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/author_list.html"
        assert len(res.context["object_list"]) == 30
        assert res.context["author_list"] is res.context["object_list"]
        assert res.context["author_list"][0].name == "Author 30"
        assert res.context["page_obj"].number == 2

    def test_paginated_custom_paginator_constructor(self):
        self._make_authors(7)
        res = client.get("/list/authors/paginated/custom_constructor/")
        assert res.status_code == 200
        # Custom pagination allows for 2 orphans on a page size of 5
        assert len(res.context["object_list"]) == 7

    def test_paginated_orphaned_queryset(self):
        self._make_authors(92)
        res = client.get("/list/authors/paginated-orphaned/")
        assert res.status_code == 200
        assert res.context["page_obj"].number == 1
        res = client.get("/list/authors/paginated-orphaned/", {"page": "last"})
        assert res.status_code == 200
        assert res.context["page_obj"].number == 3
        res = client.get("/list/authors/paginated-orphaned/", {"page": "3"})
        assert res.status_code == 200
        assert res.context["page_obj"].number == 3
        res = client.get("/list/authors/paginated-orphaned/", {"page": "4"})
        assert res.status_code == 404

    def test_paginated_non_queryset(self):
        res = self.client.get("/list/dict/paginated/")

        assert res.status_code == 200
        assert len(res.context["object_list"]) == 1

    def test_verbose_name(self):
        res = client.get("/list/artists/")
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/list.html"
        assert list(res.context["object_list"]) == list(Artist.objects.all())
        assert res.context["artist_list"] is res.context["object_list"]
        assert res.context["paginator"] is None
        assert res.context["page_obj"] is None
        assert res.context["is_paginated"] is False

    def test_allow_empty_false(self):
        res = client.get("/list/authors/notempty/")
        assert res.status_code == 200
        Author.objects.all().delete()
        res = client.get("/list/authors/notempty/")
        assert res.status_code == 404

    def test_template_name(self):
        res = client.get("/list/authors/template_name/")
        assert res.status_code == 200
        assert list(res.context["object_list"]) == list(Author.objects.all())
        assert res.context["author_list"] is res.context["object_list"]
        assert res.template_name[0] == "test_generic_views/list.html"

    def test_template_name_suffix(self):
        res = client.get("/list/authors/template_name_suffix/")
        assert res.status_code == 200
        assert list(res.context["object_list"]) == list(Author.objects.all())
        assert res.context["author_list"] is res.context["object_list"]
        assert res.template_name[0] == "test_generic_views/author_objects.html"

    def test_context_object_name(self):
        res = client.get("/list/authors/context_object_name/")
        assert res.status_code == 200
        assert list(res.context["object_list"]) == list(Author.objects.all())
        assert "authors" not in res.context
        assert res.context["author_list"] is res.context["object_list"]
        assert res.template_name[0] == "test_generic_views/author_list.html"

    def test_duplicate_context_object_name(self):
        res = client.get("/list/authors/dupe_context_object_name/")
        assert res.status_code == 200
        assert list(res.context["object_list"]) == list(Author.objects.all())
        assert "authors" not in res.context
        assert "author_list" not in res.context
        assert res.template_name[0] == "test_generic_views/author_list.html"

    def test_missing_items(self):
        msg = (
            "AuthorList is missing a QuerySet. Define AuthorList.model, "
            "AuthorList.queryset, or override AuthorList.get_queryset()."
        )
        with pytest.raises(ImproperlyConfigured, match=msg):
            client.get("/list/authors/invalid/")

    def test_invalid_get_queryset(self):
        msg = re.escape(
            "AuthorListGetQuerysetReturnsNone requires either a 'template_name' "
            "attribute or a get_queryset() method that returns a QuerySet."
        )
        with pytest.raises(ImproperlyConfigured, match=msg):
            client.get("/list/authors/get_queryset/")

    def test_paginated_list_view_does_not_load_entire_table(self):
        # Regression test for #17535
        self._make_authors(3)
        # 1 query for authors
        with self.assertNumQueries(1):
            client.get("/list/authors/notempty/")
        # same as above + 1 query to test if authors exist + 1 query for pagination
        with self.assertNumQueries(3):
            client.get("/list/authors/notempty/paginated/")

    def test_explicitly_ordered_list_view(self):
        Book.objects.create(
            name="Zebras for Dummies", pages=800, pubdate=datetime.date(2006, 9, 1)
        )
        res = self.client.get("/list/books/sorted/")
        assert res.status_code == 200
        assert res.context["object_list"][0].name == "2066"
        assert res.context["object_list"][1].name == "Dreaming in Code"
        assert res.context["object_list"][2].name == "Zebras for Dummies"

        res = client.get("/list/books/sortedbypagesandnamedec/")
        assert res.status_code == 200
        assert res.context["object_list"][0].name == "Dreaming in Code"
        assert res.context["object_list"][1].name == "Zebras for Dummies"
        assert res.context["object_list"][2].name == "2066"

    @pytest.fixture(autouse=True)
    def toggle_debug_tests(self, settings):
        settings.DEBUG = True

    def test_paginated_list_view_returns_useful_message_on_invalid_page(self):
        # test for #19240
        # tests that source exception's message is included in page
        self._make_authors(1)
        res = client.get("/list/authors/paginated/2/")
        assert res.status_code == 404
        assert (
            res.context.get("reason")
            == "Invalid page (2): That page contains no results"
        )

    def _make_authors(self, n):
        Author.objects.all().delete()
        for i in range(n):
            Author.objects.create(name="Author %02i" % i, slug="a%s" % i)
