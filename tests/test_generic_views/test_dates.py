import datetime

import pytest
from django.db import connection
from pytest_django.asserts import assertNumQueries

from django.core.exceptions import ImproperlyConfigured
from django.test import Client
from django.test.utils import TZ_SUPPORT

from .models import Artist, Author, Book, BookSigning, Page

client = Client()


def _make_books(n, base_date):
    for i in range(n):
        Book.objects.create(
            name="Book %d" % i,
            slug="book-%d" % i,
            pages=100 + i,
            pubdate=base_date - datetime.timedelta(days=i),
        )


class TestDataMixin:
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
            template="generic_views/page_template.html",
        )


@pytest.fixture(autouse=True)
def url_setting_set(settings):
    old_root_urlconf = settings.ROOT_URLCONF
    settings.ROOT_URLCONF = "test_generic_views.urls"
    yield settings
    settings.ROOT_URLCONF = old_root_urlconf


@pytest.mark.django_db
class TestArchiveIndexView(TestDataMixin):
    def test_archive_view(self):
        res = client.get("/dates/books/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == list(
            Book.objects.dates("pubdate", "year", "DESC")
        )
        assert list(res.context["latest"]) == list(Book.objects.all())
        assert res.template_name[0] == "test_generic_views/book_archive.html"

    def test_archive_view_context_object_name(self):
        res = client.get("/dates/books/context_object_name/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == list(
            Book.objects.dates("pubdate", "year", "DESC")
        )
        assert list(res.context["thingies"]) == list(Book.objects.all())
        assert "latest" not in res.context
        assert res.template_name[0] == "test_generic_views/book_archive.html"

    def test_empty_archive_view(self):
        Book.objects.all().delete()
        res = client.get("/dates/books/")
        assert res.status_code == 404

    def test_allow_empty_archive_view(self):
        Book.objects.all().delete()
        res = client.get("/dates/books/allow_empty/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == []
        assert res.template_name[0] == "test_generic_views/book_archive.html"

    def test_archive_view_template(self):
        res = client.get("/dates/books/template_name/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == list(
            Book.objects.dates("pubdate", "year", "DESC")
        )
        assert list(res.context["latest"]) == list(Book.objects.all())
        assert res.template_name[0] == "test_generic_views/list.html"

    def test_archive_view_template_suffix(self):
        res = client.get("/dates/books/template_name_suffix/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == list(
            Book.objects.dates("pubdate", "year", "DESC")
        )
        assert list(res.context["latest"]) == list(Book.objects.all())
        assert res.template_name[0] == "test_generic_views/book_detail.html"

    def test_archive_view_invalid(self):
        msg = (
            "BookArchive is missing a QuerySet. Define BookArchive.model, "
            "BookArchive.queryset, or override BookArchive.get_queryset()."
        )
        with pytest.raises(ImproperlyConfigured, match=msg):
            client.get("/dates/books/invalid/")

    def test_archive_view_by_month(self):
        res = client.get("/dates/books/by_month/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == list(
            Book.objects.dates("pubdate", "month", "DESC")
        )

    def test_paginated_archive_view(self):
        _make_books(20, base_date=datetime.date.today())
        res = client.get("/dates/books/paginated/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == list(
            Book.objects.dates("pubdate", "year", "DESC")
        )
        assert list(res.context["latest"]) == list(Book.objects.all()[0:10])
        assert res.template_name[0] == "test_generic_views/book_archive.html"

        res = client.get("/dates/books/paginated/?page=2")
        assert res.status_code == 200
        assert res.context["page_obj"].number == 2
        assert list(res.context["latest"]) == list(Book.objects.all()[10:20])

    def test_paginated_archive_view_does_not_load_entire_table(self):
        # Regression test for #18087
        _make_books(20, base_date=datetime.date.today())
        # 1 query for years list + 1 query for books
        with assertNumQueries(2):
            client.get("/dates/books/")
        # same as above + 1 query to test if books exist + 1 query to count them
        with assertNumQueries(4):
            client.get("/dates/books/paginated/")

    def test_no_duplicate_query(self):
        # Regression test for #18354
        with assertNumQueries(2):
            client.get("/dates/books/reverse/")

    def test_datetime_archive_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0))
        res = client.get("/dates/booksignings/")
        assert res.status_code == 200

    @pytest.mark.skipif(
        not TZ_SUPPORT,
        reason="This test relies on the ability to run a program in an arbitrary "
        "time zone, but your operating system isn't able to do that.",
    )
    @pytest.mark.skipif(
        not getattr(connection.features, "has_zoneinfo_database", False),
        reason="Database doesn't support zoneinfo",
    )
    def test_aware_datetime_archive_view(self, settings):
        settings.USE_TZ = True
        settings.TIME_ZONE = "Africa/Nairobi"
        BookSigning.objects.create(
            event_date=datetime.datetime(
                2008, 4, 2, 12, 0, tzinfo=datetime.timezone.utc
            )
        )
        res = client.get("/dates/booksignings/")
        assert res.status_code == 200

    def test_date_list_order(self):
        """date_list should be sorted descending in index"""
        _make_books(5, base_date=datetime.date(2011, 12, 25))
        res = client.get("/dates/books/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == sorted(
            res.context["date_list"], reverse=True
        )

    def test_archive_view_custom_sorting(self):
        Book.objects.create(
            name="Zebras for Dummies", pages=600, pubdate=datetime.date(2007, 5, 1)
        )
        res = client.get("/dates/books/sortedbyname/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == list(
            Book.objects.dates("pubdate", "year", "DESC")
        )
        assert list(res.context["latest"]) == list(Book.objects.order_by("name").all())
        assert res.template_name[0] == "test_generic_views/book_archive.html"

    def test_archive_view_custom_sorting_dec(self):
        Book.objects.create(
            name="Zebras for Dummies", pages=600, pubdate=datetime.date(2007, 5, 1)
        )
        res = client.get("/dates/books/sortedbynamedec/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == list(
            Book.objects.dates("pubdate", "year", "DESC")
        )
        assert list(res.context["latest"]) == list(Book.objects.order_by("-name").all())
        assert res.template_name[0] == "test_generic_views/book_archive.html"

    def test_archive_view_without_date_field(self):
        msg = "BookArchiveWithoutDateField.date_field is required."
        with pytest.raises(ImproperlyConfigured, match=msg):
            client.get("/dates/books/without_date_field/")


@pytest.mark.django_db
class TestYearArchiveView(TestDataMixin):
    def test_year_view(self):
        res = client.get("/dates/books/2008/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == [datetime.date(2008, 10, 1)]
        assert res.context["year"] == datetime.date(2008, 1, 1)
        assert res.template_name[0] == "test_generic_views/book_archive_year.html"

        # Since allow_empty=False, next/prev years must be valid (#7164)
        assert res.context["next_year"] is None
        assert res.context["previous_year"] == datetime.date(2006, 1, 1)

    def test_year_view_make_object_list(self):
        res = client.get("/dates/books/2006/make_object_list/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == [datetime.date(2006, 5, 1)]
        assert list(res.context["book_list"]) == list(
            Book.objects.filter(pubdate__year=2006)
        )
        assert list(res.context["object_list"]) == list(
            Book.objects.filter(pubdate__year=2006)
        )
        assert res.template_name[0] == "test_generic_views/book_archive_year.html"

    def test_year_view_empty(self):
        res = client.get("/dates/books/1999/")
        assert res.status_code == 404
        res = client.get("/dates/books/1999/allow_empty/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == []
        assert list(res.context["book_list"]) == []

        # Since allow_empty=True, next/prev are allowed to be empty years (#7164)
        assert res.context["next_year"] == datetime.date(2000, 1, 1)
        assert res.context["previous_year"] == datetime.date(1998, 1, 1)

    def test_year_view_allow_future(self):
        # Create a new book in the future
        year = datetime.date.today().year + 1
        Book.objects.create(
            name="The New New Testement", pages=600, pubdate=datetime.date(year, 1, 1)
        )
        res = client.get("/dates/books/%s/" % year)
        assert res.status_code == 404

        res = client.get("/dates/books/%s/allow_empty/" % year)
        assert res.status_code == 200
        assert list(res.context["book_list"]) == []

        res = client.get("/dates/books/%s/allow_future/" % year)
        assert res.status_code == 200
        assert list(res.context["date_list"]) == [datetime.date(year, 1, 1)]

    def test_year_view_paginated(self):
        res = client.get("/dates/books/2006/paginated/")
        assert res.status_code == 200
        assert list(res.context["book_list"]) == list(
            Book.objects.filter(pubdate__year=2006)
        )
        assert list(res.context["object_list"]) == list(
            Book.objects.filter(pubdate__year=2006)
        )
        assert res.template_name[0] == "test_generic_views/book_archive_year.html"

    def test_year_view_custom_sort_order(self):
        # Zebras comes after Dreaming by name, but before on '-pubdate' which
        # is the default sorting.
        Book.objects.create(
            name="Zebras for Dummies", pages=600, pubdate=datetime.date(2006, 9, 1)
        )
        res = client.get("/dates/books/2006/sortedbyname/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == [
            datetime.date(2006, 5, 1),
            datetime.date(2006, 9, 1),
        ]
        assert list(res.context["book_list"]) == list(
            Book.objects.filter(pubdate__year=2006).order_by("name")
        )
        assert list(res.context["object_list"]) == list(
            Book.objects.filter(pubdate__year=2006).order_by("name")
        )
        assert res.template_name[0] == "test_generic_views/book_archive_year.html"

    def test_year_view_two_custom_sort_orders(self):
        Book.objects.create(
            name="Zebras for Dummies", pages=300, pubdate=datetime.date(2006, 9, 1)
        )
        Book.objects.create(
            name="Hunting Hippos", pages=400, pubdate=datetime.date(2006, 3, 1)
        )
        res = client.get("/dates/books/2006/sortedbypageandnamedec/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == [
            datetime.date(2006, 3, 1),
            datetime.date(2006, 5, 1),
            datetime.date(2006, 9, 1),
        ]
        assert list(res.context["book_list"]) == list(
            Book.objects.filter(pubdate__year=2006).order_by("pages", "-name")
        )
        assert list(res.context["object_list"]) == list(
            Book.objects.filter(pubdate__year=2006).order_by("pages", "-name")
        )
        assert res.template_name[0] == "test_generic_views/book_archive_year.html"

    def test_year_view_invalid_pattern(self):
        res = client.get("/dates/books/no_year/")
        assert res.status_code == 404

    def test_no_duplicate_query(self):
        # Regression test for #18354
        with assertNumQueries(4):
            client.get("/dates/books/2008/reverse/")

    def test_datetime_year_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0))
        res = client.get("/dates/booksignings/2008/")
        assert res.status_code == 200

    @pytest.mark.skipif(
        not getattr(connection.features, "has_zoneinfo_database", False),
        reason="Database doesn't support zoneinfo",
    )
    def test_aware_datetime_year_view(self, settings):
        settings.USE_TZ = True
        settings.TIME_ZONE = "Africa/Nairobi"
        BookSigning.objects.create(
            event_date=datetime.datetime(
                2008, 4, 2, 12, 0, tzinfo=datetime.timezone.utc
            )
        )
        res = client.get("/dates/booksignings/2008/")
        assert res.status_code == 200

    def test_date_list_order(self):
        """date_list should be sorted ascending in year view"""
        _make_books(10, base_date=datetime.date(2011, 12, 25))
        res = client.get("/dates/books/2011/")
        assert list(res.context["date_list"]) == sorted(res.context["date_list"])

    def test_get_context_data_receives_extra_context(self, mocker):
        """
        MultipleObjectMixin.get_context_data() receives the context set by
        BaseYearArchiveView.get_dated_items(). This behavior is implemented in
        BaseDateListView.get().
        """
        mock = mocker.patch(
            "django_async_extensions.aviews.generic.list.AsyncMultipleObjectMixin.get_context_data"
        )
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0))
        with pytest.raises(
            TypeError, match="context must be a dict rather than AsyncMock."
        ):
            client.get("/dates/booksignings/2008/")

        args, kwargs = mock.call_args
        # These are context values from get_dated_items().
        assert kwargs["year"] == datetime.date(2008, 1, 1)
        assert kwargs["previous_year"] is None
        assert kwargs["next_year"] is None

    def test_get_dated_items_not_implemented(self):
        msg = "An AsyncDateView must provide an implementation of get_dated_items()"
        with pytest.raises(NotImplementedError, match=msg):
            client.get("/BaseDateListViewTest/")


@pytest.mark.django_db
class TestMonthArchiveView(TestDataMixin):
    def test_month_view(self):
        res = client.get("/dates/books/2008/oct/")
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/book_archive_month.html"
        assert list(res.context["date_list"]) == [datetime.date(2008, 10, 1)]
        assert list(res.context["book_list"]) == list(
            Book.objects.filter(pubdate=datetime.date(2008, 10, 1))
        )
        assert res.context["month"] == datetime.date(2008, 10, 1)

        # Since allow_empty=False, next/prev months must be valid (#7164)
        assert res.context["next_month"] is None
        assert res.context["previous_month"] == datetime.date(2006, 5, 1)

    def test_month_view_allow_empty(self):
        # allow_empty = False, empty month
        res = client.get("/dates/books/2000/jan/")
        assert res.status_code == 404

        # allow_empty = True, empty month
        res = client.get("/dates/books/2000/jan/allow_empty/")
        assert res.status_code == 200
        assert list(res.context["date_list"]) == []
        assert list(res.context["book_list"]) == []
        assert res.context["month"] == datetime.date(2000, 1, 1)

        # Since allow_empty=True, next/prev are allowed to be empty months (#7164)
        assert res.context["next_month"] == datetime.date(2000, 2, 1)
        assert res.context["previous_month"] == datetime.date(1999, 12, 1)

        # allow_empty but not allow_future: next_month should be empty (#7164)
        url = datetime.date.today().strftime("/dates/books/%Y/%b/allow_empty/").lower()
        res = client.get(url)
        assert res.status_code == 200
        assert res.context["next_month"] is None

    def test_month_view_allow_future(self):
        future = (datetime.date.today() + datetime.timedelta(days=60)).replace(day=1)
        urlbit = future.strftime("%Y/%b").lower()
        b = Book.objects.create(name="The New New Testement", pages=600, pubdate=future)

        # allow_future = False, future month
        res = client.get("/dates/books/%s/" % urlbit)
        assert res.status_code == 404

        # allow_future = True, valid future month
        res = client.get("/dates/books/%s/allow_future/" % urlbit)
        assert res.status_code == 200
        assert res.context["date_list"][0] == b.pubdate
        assert list(res.context["book_list"]) == [b]
        assert res.context["month"] == future

        # Since allow_future = True but not allow_empty, next/prev are not
        # allowed to be empty months (#7164)
        assert res.context["next_month"] is None
        assert res.context["previous_month"] == datetime.date(2008, 10, 1)

        # allow_future, but not allow_empty, with a current month. So next
        # should be in the future (yup, #7164, again)
        res = client.get("/dates/books/2008/oct/allow_future/")
        assert res.status_code == 200
        assert res.context["next_month"] == future
        assert res.context["previous_month"] == datetime.date(2006, 5, 1)

    def test_month_view_paginated(self):
        res = client.get("/dates/books/2008/oct/paginated/")
        assert res.status_code == 200
        assert list(res.context["book_list"]) == list(
            Book.objects.filter(pubdate__year=2008, pubdate__month=10)
        )
        assert list(res.context["object_list"]) == list(
            Book.objects.filter(pubdate__year=2008, pubdate__month=10)
        )
        assert res.template_name[0] == "test_generic_views/book_archive_month.html"

    def test_custom_month_format(self):
        res = client.get("/dates/books/2008/10/")
        assert res.status_code == 200

    def test_month_view_invalid_pattern(self):
        res = client.get("/dates/books/2007/no_month/")
        assert res.status_code == 404

    def test_previous_month_without_content(self):
        "Content can exist on any day of the previous month. Refs #14711"
        self.pubdate_list = [
            datetime.date(2010, month, day) for month, day in ((9, 1), (10, 2), (11, 3))
        ]
        for pubdate in self.pubdate_list:
            name = str(pubdate)
            Book.objects.create(name=name, slug=name, pages=100, pubdate=pubdate)

        res = client.get("/dates/books/2010/nov/allow_empty/")
        assert res.status_code == 200
        assert res.context["previous_month"] == datetime.date(2010, 10, 1)
        # The following test demonstrates the bug
        res = client.get("/dates/books/2010/nov/")
        assert res.status_code == 200
        assert res.context["previous_month"] == datetime.date(2010, 10, 1)
        # The bug does not occur here because a Book with pubdate of Sep 1 exists
        res = client.get("/dates/books/2010/oct/")
        assert res.status_code == 200
        assert res.context["previous_month"] == datetime.date(2010, 9, 1)

    def test_datetime_month_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 2, 1, 12, 0))
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0))
        BookSigning.objects.create(event_date=datetime.datetime(2008, 6, 3, 12, 0))
        res = client.get("/dates/booksignings/2008/apr/")
        assert res.status_code == 200

    def test_month_view_get_month_from_request(self):
        oct1 = datetime.date(2008, 10, 1)
        res = client.get("/dates/books/without_month/2008/?month=oct")
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/book_archive_month.html"
        assert list(res.context["date_list"]) == [oct1]
        assert list(res.context["book_list"]) == list(Book.objects.filter(pubdate=oct1))
        assert res.context["month"] == oct1

    def test_month_view_without_month_in_url(self):
        res = client.get("/dates/books/without_month/2008/")
        assert res.status_code == 404
        assert res.context["exception"] == "No month specified"

    @pytest.mark.skipif(
        not getattr(connection.features, "has_zoneinfo_database", False),
        reason="Database doesn't support zoneinfo",
    )
    def test_aware_datetime_month_view(self, settings):
        settings.USE_TZ = True
        settings.TIME_ZONE = "Africa/Nairobi"
        BookSigning.objects.create(
            event_date=datetime.datetime(
                2008, 2, 1, 12, 0, tzinfo=datetime.timezone.utc
            )
        )
        BookSigning.objects.create(
            event_date=datetime.datetime(
                2008, 4, 2, 12, 0, tzinfo=datetime.timezone.utc
            )
        )
        BookSigning.objects.create(
            event_date=datetime.datetime(
                2008, 6, 3, 12, 0, tzinfo=datetime.timezone.utc
            )
        )
        res = client.get("/dates/booksignings/2008/apr/")
        assert res.status_code == 200

    def test_date_list_order(self):
        """date_list should be sorted ascending in month view"""
        _make_books(10, base_date=datetime.date(2011, 12, 25))
        res = client.get("/dates/books/2011/dec/")
        assert list(res.context["date_list"]) == sorted(res.context["date_list"])


@pytest.mark.django_db
class TestWeekArchiveView(TestDataMixin):
    def test_week_view(self):
        res = client.get("/dates/books/2008/week/39/")
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/book_archive_week.html"
        assert res.context["book_list"][0] == Book.objects.get(
            pubdate=datetime.date(2008, 10, 1)
        )
        assert res.context["week"] == datetime.date(2008, 9, 28)

        # Since allow_empty=False, next/prev weeks must be valid
        assert res.context["next_week"] is None
        assert res.context["previous_week"] == datetime.date(2006, 4, 30)

    def test_week_view_allow_empty(self):
        # allow_empty = False, empty week
        res = client.get("/dates/books/2008/week/12/")
        assert res.status_code == 404

        # allow_empty = True, empty month
        res = client.get("/dates/books/2008/week/12/allow_empty/")
        assert res.status_code == 200
        assert list(res.context["book_list"]) == []
        assert res.context["week"] == datetime.date(2008, 3, 23)

        # Since allow_empty=True, next/prev are allowed to be empty weeks
        assert res.context["next_week"] == datetime.date(2008, 3, 30)
        assert res.context["previous_week"] == datetime.date(2008, 3, 16)

        # allow_empty but not allow_future: next_week should be empty
        url = (
            datetime.date.today()
            .strftime("/dates/books/%Y/week/%U/allow_empty/")
            .lower()
        )
        res = client.get(url)
        assert res.status_code == 200
        assert res.context["next_week"] is None

    def test_week_view_allow_future(self):
        # January 7th always falls in week 1, given Python's definition of week numbers
        future = datetime.date(datetime.date.today().year + 1, 1, 7)
        future_sunday = future - datetime.timedelta(days=(future.weekday() + 1) % 7)
        b = Book.objects.create(name="The New New Testement", pages=600, pubdate=future)

        res = client.get("/dates/books/%s/week/1/" % future.year)
        assert res.status_code == 404

        res = client.get("/dates/books/%s/week/1/allow_future/" % future.year)
        assert res.status_code == 200
        assert list(res.context["book_list"]) == [b]
        assert res.context["week"] == future_sunday

        # Since allow_future = True but not allow_empty, next/prev are not
        # allowed to be empty weeks
        assert res.context["next_week"] is None
        assert res.context["previous_week"] == datetime.date(2008, 9, 28)

        # allow_future, but not allow_empty, with a current week. So next
        # should be in the future
        res = client.get("/dates/books/2008/week/39/allow_future/")
        assert res.status_code == 200
        assert res.context["next_week"] == future_sunday
        assert res.context["previous_week"] == datetime.date(2006, 4, 30)

    def test_week_view_paginated(self):
        week_start = datetime.date(2008, 9, 28)
        week_end = week_start + datetime.timedelta(days=7)
        res = client.get("/dates/books/2008/week/39/")
        assert res.status_code == 200
        assert list(res.context["book_list"]) == list(
            Book.objects.filter(pubdate__gte=week_start, pubdate__lt=week_end)
        )

        assert list(res.context["object_list"]) == list(
            Book.objects.filter(pubdate__gte=week_start, pubdate__lt=week_end)
        )
        assert list(res.context["object_list"]) == list(
            Book.objects.filter(pubdate__gte=week_start, pubdate__lt=week_end)
        )
        assert res.template_name[0] == "test_generic_views/book_archive_week.html"

    def test_week_view_invalid_pattern(self):
        res = client.get("/dates/books/2007/week/no_week/")
        assert res.status_code == 404

    def test_week_start_Monday(self):
        # Regression for #14752
        res = client.get("/dates/books/2008/week/39/")
        assert res.status_code == 200
        assert res.context["week"] == datetime.date(2008, 9, 28)

        res = client.get("/dates/books/2008/week/39/monday/")
        assert res.status_code == 200
        assert res.context["week"] == datetime.date(2008, 9, 29)

    def test_week_iso_format(self):
        res = client.get("/dates/books/2008/week/40/iso_format/")
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/book_archive_week.html"
        assert list(res.context["book_list"]) == [
            Book.objects.get(pubdate=datetime.date(2008, 10, 1))
        ]
        assert res.context["week"] == datetime.date(2008, 9, 29)

    def test_unknown_week_format(self):
        msg = "Unknown week format '%T'. Choices are: %U, %V, %W"
        with pytest.raises(ValueError, match=msg):
            client.get("/dates/books/2008/week/39/unknown_week_format/")

    def test_incompatible_iso_week_format_view(self):
        msg = (
            "ISO week directive '%V' is incompatible with the year directive "
            "'%Y'. Use the ISO year '%G' instead."
        )
        with pytest.raises(ValueError, match=msg):
            client.get("/dates/books/2008/week/40/invalid_iso_week_year_format/")

    def test_datetime_week_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0))
        res = client.get("/dates/booksignings/2008/week/13/")
        assert res.status_code == 200

    def test_aware_datetime_week_view(self, settings):
        settings.USE_TZ = True
        settings.TIME_ZONE = "Africa/Nairobi"
        BookSigning.objects.create(
            event_date=datetime.datetime(
                2008, 4, 2, 12, 0, tzinfo=datetime.timezone.utc
            )
        )
        res = client.get("/dates/booksignings/2008/week/13/")
        assert res.status_code == 200


@pytest.mark.django_db
class TestDayArchiveView(TestDataMixin):
    def test_day_view(self):
        res = client.get("/dates/books/2008/oct/01/")
        assert res.status_code == 200
        assert res.template_name[0] == "test_generic_views/book_archive_day.html"
        assert list(res.context["book_list"]) == list(
            Book.objects.filter(pubdate=datetime.date(2008, 10, 1))
        )
        assert res.context["day"] == datetime.date(2008, 10, 1)

        # Since allow_empty=False, next/prev days must be valid.
        assert res.context["next_day"] is None
        assert res.context["previous_day"] == datetime.date(2006, 5, 1)

    def test_day_view_allow_empty(self):
        # allow_empty = False, empty month
        res = client.get("/dates/books/2000/jan/1/")
        assert res.status_code == 404

        # allow_empty = True, empty month
        res = client.get("/dates/books/2000/jan/1/allow_empty/")
        assert res.status_code == 200
        assert list(res.context["book_list"]) == []
        assert res.context["day"] == datetime.date(2000, 1, 1)

        # Since it's allow empty, next/prev are allowed to be empty months (#7164)
        assert res.context["next_day"] == datetime.date(2000, 1, 2)
        assert res.context["previous_day"] == datetime.date(1999, 12, 31)

        # allow_empty but not allow_future: next_month should be empty (#7164)
        url = (
            datetime.date.today().strftime("/dates/books/%Y/%b/%d/allow_empty/").lower()
        )
        res = client.get(url)
        assert res.status_code == 200
        assert res.context["next_day"] is None

    def test_day_view_allow_future(self):
        future = datetime.date.today() + datetime.timedelta(days=60)
        urlbit = future.strftime("%Y/%b/%d").lower()
        b = Book.objects.create(name="The New New Testement", pages=600, pubdate=future)

        # allow_future = False, future month
        res = client.get("/dates/books/%s/" % urlbit)
        assert res.status_code == 404

        # allow_future = True, valid future month
        res = client.get("/dates/books/%s/allow_future/" % urlbit)
        assert res.status_code == 200
        assert list(res.context["book_list"]) == [b]
        assert res.context["day"] == future

        # allow_future but not allow_empty, next/prev must be valid
        assert res.context["next_day"] is None
        assert res.context["previous_day"] == datetime.date(2008, 10, 1)

        # allow_future, but not allow_empty, with a current month.
        res = client.get("/dates/books/2008/oct/01/allow_future/")
        assert res.status_code == 200
        assert res.context["next_day"] == future
        assert res.context["previous_day"] == datetime.date(2006, 5, 1)

        # allow_future for yesterday, next_day is today (#17192)
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        res = client.get(
            "/dates/books/%s/allow_empty_and_future/"
            % yesterday.strftime("%Y/%b/%d").lower()
        )
        assert res.context["next_day"] == today

    def test_day_view_paginated(self):
        res = client.get("/dates/books/2008/oct/1/")
        assert res.status_code == 200
        assert list(res.context["book_list"]) == list(
            Book.objects.filter(pubdate__year=2008, pubdate__month=10, pubdate__day=1)
        )
        assert list(res.context["object_list"]) == list(
            Book.objects.filter(pubdate__year=2008, pubdate__month=10, pubdate__day=1)
        )
        assert res.template_name[0] == "test_generic_views/book_archive_day.html"

    def test_next_prev_context(self):
        res = client.get("/dates/books/2008/oct/01/")
        assert res.content == b"Archive for Oct. 1, 2008. Previous day is May 1, 2006\n"

    def test_custom_month_format(self):
        res = client.get("/dates/books/2008/10/01/")
        assert res.status_code == 200

    def test_day_view_invalid_pattern(self):
        res = client.get("/dates/books/2007/oct/no_day/")
        assert res.status_code == 404

    def test_today_view(self):
        res = client.get("/dates/books/today/")
        assert res.status_code == 404
        res = client.get("/dates/books/today/allow_empty/")
        assert res.status_code == 200
        assert res.context["day"] == datetime.date.today()

    def test_datetime_day_view(self):
        BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0))
        res = client.get("/dates/booksignings/2008/apr/2/")
        assert res.status_code == 200

    @pytest.mark.skipif(
        not TZ_SUPPORT,
        reason="This test relies on the ability to run a program in an arbitrary "
        "time zone, but your operating system isn't able to do that.",
    )
    def test_aware_datetime_day_view(self, settings):
        settings.USE_TZ = True
        settings.TIME_ZONE = "Africa/Nairobi"

        bs = BookSigning.objects.create(
            event_date=datetime.datetime(
                2008, 4, 2, 12, 0, tzinfo=datetime.timezone.utc
            )
        )
        res = client.get("/dates/booksignings/2008/apr/2/")
        assert res.status_code == 200
        # 2008-04-02T00:00:00+03:00 (beginning of day) >
        # 2008-04-01T22:00:00+00:00 (book signing event date).
        bs.event_date = datetime.datetime(
            2008, 4, 1, 22, 0, tzinfo=datetime.timezone.utc
        )
        bs.save()
        res = client.get("/dates/booksignings/2008/apr/2/")
        assert res.status_code == 200
        # 2008-04-03T00:00:00+03:00 (end of day) > 2008-04-02T22:00:00+00:00
        # (book signing event date).
        bs.event_date = datetime.datetime(
            2008, 4, 2, 22, 0, tzinfo=datetime.timezone.utc
        )
        bs.save()
        res = client.get("/dates/booksignings/2008/apr/2/")
        assert res.status_code == 404


@pytest.mark.django_db
class TestDateDetailView(TestDataMixin):
    def test_date_detail_by_pk(self):
        res = client.get("/dates/books/2008/oct/01/%s/" % self.book1.pk)
        assert res.status_code == 200
        assert res.context["object"] == self.book1
        assert res.context["book"] == self.book1
        assert res.template_name[0] == "test_generic_views/book_detail.html"

    def test_date_detail_by_slug(self):
        res = client.get("/dates/books/2006/may/01/byslug/dreaming-in-code/")
        assert res.status_code == 200
        assert res.context["book"] == Book.objects.get(slug="dreaming-in-code")

    def test_date_detail_custom_month_format(self):
        res = client.get("/dates/books/2008/10/01/%s/" % self.book1.pk)
        assert res.status_code == 200
        assert res.context["book"] == self.book1

    def test_date_detail_allow_future(self):
        future = datetime.date.today() + datetime.timedelta(days=60)
        urlbit = future.strftime("%Y/%b/%d").lower()
        b = Book.objects.create(
            name="The New New Testement", slug="new-new", pages=600, pubdate=future
        )

        res = client.get("/dates/books/%s/new-new/" % urlbit)
        assert res.status_code == 404

        res = client.get("/dates/books/%s/%s/allow_future/" % (urlbit, b.id))
        assert res.status_code == 200
        assert res.context["book"] == b
        assert res.template_name[0] == "test_generic_views/book_detail.html"

    def test_year_out_of_range(self, subtests):
        urls = [
            "/dates/books/9999/",
            "/dates/books/9999/12/",
            "/dates/books/9999/week/52/",
        ]
        for url in urls:
            with subtests.test(url=url):
                res = client.get(url)
                assert res.status_code == 404
                assert res.context["exception"] == "Date out of range"

    def test_invalid_url(self):
        msg = (
            "Generic detail view BookDetail must be called with either an "
            "object pk or a slug in the URLconf."
        )
        with pytest.raises(AttributeError, match=msg):
            client.get("/dates/books/2008/oct/01/nopk/")

    def test_get_object_custom_queryset(self):
        """
        Custom querysets are used when provided to
        BaseDateDetailView.get_object().
        """
        res = client.get(
            "/dates/books/get_object_custom_queryset/2006/may/01/%s/" % self.book2.pk
        )
        assert res.status_code == 200
        assert res.context["object"] == self.book2
        assert res.context["book"] == self.book2
        assert res.template_name[0] == "test_generic_views/book_detail.html"

        res = client.get("/dates/books/get_object_custom_queryset/2008/oct/01/9999999/")
        assert res.status_code == 404

    def test_get_object_custom_queryset_numqueries(self):
        with assertNumQueries(1):
            client.get("/dates/books/get_object_custom_queryset/2006/may/01/2/")

    def test_datetime_date_detail(self):
        bs = BookSigning.objects.create(event_date=datetime.datetime(2008, 4, 2, 12, 0))
        res = client.get("/dates/booksignings/2008/apr/2/%d/" % bs.pk)
        assert res.status_code == 200

    @pytest.mark.skipif(
        not TZ_SUPPORT,
        reason="This test relies on the ability to run a program in an arbitrary "
        "time zone, but your operating system isn't able to do that.",
    )
    def test_aware_datetime_date_detail(self, settings):
        settings.USE_TZ = True
        settings.TIME_ZONE = "Africa/Nairobi"
        bs = BookSigning.objects.create(
            event_date=datetime.datetime(
                2008, 4, 2, 12, 0, tzinfo=datetime.timezone.utc
            )
        )
        res = client.get("/dates/booksignings/2008/apr/2/%d/" % bs.pk)
        assert res.status_code == 200
        # 2008-04-02T00:00:00+03:00 (beginning of day) >
        # 2008-04-01T22:00:00+00:00 (book signing event date).
        bs.event_date = datetime.datetime(
            2008, 4, 1, 22, 0, tzinfo=datetime.timezone.utc
        )
        bs.save()
        res = client.get("/dates/booksignings/2008/apr/2/%d/" % bs.pk)
        assert res.status_code == 200
        # 2008-04-03T00:00:00+03:00 (end of day) > 2008-04-02T22:00:00+00:00
        # (book signing event date).
        bs.event_date = datetime.datetime(
            2008, 4, 2, 22, 0, tzinfo=datetime.timezone.utc
        )
        bs.save()
        res = client.get("/dates/booksignings/2008/apr/2/%d/" % bs.pk)
        assert res.status_code == 404
