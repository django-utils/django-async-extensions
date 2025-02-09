import collections.abc
import warnings
from datetime import datetime

import pytest
from pytest_django.asserts import assertWarnsMessage

from django.core.paginator import (
    EmptyPage,
    InvalidPage,
    PageNotAnInteger,
    UnorderedObjectListWarning,
)

from django_async_extensions.acore.paginator import AsyncPaginator

from .custom import AsyncValidAdjacentNumsPaginator
from .models import Article


class TestPaginationTests:
    """
    Tests for the Paginator and Page classes.
    """

    def check_paginator(self, params, output):
        """
        Helper method that instantiates a Paginator object from the passed
        params and then checks that its attributes match the passed output.
        """
        count, num_pages, page_range = output
        paginator = AsyncPaginator(*params)
        self.check_attribute("count", paginator, count, params)
        self.check_attribute("num_pages", paginator, num_pages, params)
        self.check_attribute("page_range", paginator, page_range, params, coerce=list)

    def check_attribute(self, name, paginator, expected, params, coerce=None):
        """
        Helper method that checks a single attribute and gives a nice error
        message upon test failure.
        """
        got = getattr(paginator, name)
        if coerce is not None:
            got = coerce(got)
        assert expected == got, (
            f"For {name}, expected {expected} but got {got}. "
            f"Paginator parameters were: {params}"
        )

    def test_paginator(self):
        """
        Tests the paginator attributes using varying inputs.
        """
        nine = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        ten = nine + [10]
        eleven = ten + [11]
        tests = (
            # Each item is 2-tuple:
            #     First tuple is Paginator parameters - object_list, per_page,
            #         orphans, and allow_empty_first_page.
            #     Second tuple is resulting Paginator attributes - count,
            #         num_pages, and page_range.
            # Ten items, varying orphans, no empty first page.
            ((ten, 4, 0, False), (10, 3, [1, 2, 3])),
            ((ten, 4, 1, False), (10, 3, [1, 2, 3])),
            ((ten, 4, 2, False), (10, 2, [1, 2])),
            ((ten, 4, 5, False), (10, 2, [1, 2])),
            ((ten, 4, 6, False), (10, 1, [1])),
            # Ten items, varying orphans, allow empty first page.
            ((ten, 4, 0, True), (10, 3, [1, 2, 3])),
            ((ten, 4, 1, True), (10, 3, [1, 2, 3])),
            ((ten, 4, 2, True), (10, 2, [1, 2])),
            ((ten, 4, 5, True), (10, 2, [1, 2])),
            ((ten, 4, 6, True), (10, 1, [1])),
            # One item, varying orphans, no empty first page.
            (([1], 4, 0, False), (1, 1, [1])),
            (([1], 4, 1, False), (1, 1, [1])),
            (([1], 4, 2, False), (1, 1, [1])),
            # One item, varying orphans, allow empty first page.
            (([1], 4, 0, True), (1, 1, [1])),
            (([1], 4, 1, True), (1, 1, [1])),
            (([1], 4, 2, True), (1, 1, [1])),
            # Zero items, varying orphans, no empty first page.
            (([], 4, 0, False), (0, 0, [])),
            (([], 4, 1, False), (0, 0, [])),
            (([], 4, 2, False), (0, 0, [])),
            # Zero items, varying orphans, allow empty first page.
            (([], 4, 0, True), (0, 1, [1])),
            (([], 4, 1, True), (0, 1, [1])),
            (([], 4, 2, True), (0, 1, [1])),
            # Number if items one less than per_page.
            (([], 1, 0, True), (0, 1, [1])),
            (([], 1, 0, False), (0, 0, [])),
            (([1], 2, 0, True), (1, 1, [1])),
            ((nine, 10, 0, True), (9, 1, [1])),
            # Number if items equal to per_page.
            (([1], 1, 0, True), (1, 1, [1])),
            (([1, 2], 2, 0, True), (2, 1, [1])),
            ((ten, 10, 0, True), (10, 1, [1])),
            # Number if items one more than per_page.
            (([1, 2], 1, 0, True), (2, 2, [1, 2])),
            (([1, 2, 3], 2, 0, True), (3, 2, [1, 2])),
            ((eleven, 10, 0, True), (11, 2, [1, 2])),
            # Number if items one more than per_page with one orphan.
            (([1, 2], 1, 1, True), (2, 1, [1])),
            (([1, 2, 3], 2, 1, True), (3, 1, [1])),
            ((eleven, 10, 1, True), (11, 1, [1])),
            # Non-integer inputs
            ((ten, "4", 1, False), (10, 3, [1, 2, 3])),
            ((ten, "4", 1, False), (10, 3, [1, 2, 3])),
            ((ten, 4, "1", False), (10, 3, [1, 2, 3])),
            ((ten, 4, "1", False), (10, 3, [1, 2, 3])),
        )
        for params, output in tests:
            self.check_paginator(params, output)

    async def test_invalid_page_number(self):
        """
        Invalid page numbers result in the correct exception being raised.
        """
        paginator = AsyncPaginator([1, 2, 3], 2)
        with pytest.raises(InvalidPage):
            await paginator.apage(3)
        with pytest.raises(PageNotAnInteger):
            await paginator.avalidate_number(None)
        with pytest.raises(PageNotAnInteger):
            await paginator.avalidate_number("x")
        with pytest.raises(PageNotAnInteger):
            await paginator.avalidate_number(1.2)

    async def test_error_messages(self):
        error_messages = {
            "invalid_page": "Wrong page number",
            "min_page": "Too small",
            "no_results": "There is nothing here",
        }
        paginator = AsyncPaginator([1, 2, 3], 2, error_messages=error_messages)
        msg = "Wrong page number"
        with pytest.raises(PageNotAnInteger, match=msg):
            await paginator.avalidate_number(1.2)
        msg = "Too small"
        with pytest.raises(EmptyPage, match=msg):
            await paginator.avalidate_number(-1)
        msg = "There is nothing here"
        with pytest.raises(EmptyPage, match=msg):
            await paginator.avalidate_number(3)

        error_messages = {"min_page": "Too small"}
        paginator = AsyncPaginator([1, 2, 3], 2, error_messages=error_messages)
        # Custom message.
        msg = "Too small"
        with pytest.raises(EmptyPage, match=msg):
            await paginator.avalidate_number(-1)
        # Default message.
        msg = "That page contains no results"
        with pytest.raises(EmptyPage, match=msg):
            await paginator.avalidate_number(3)

    async def test_float_integer_page(self):
        paginator = AsyncPaginator([1, 2, 3], 2)
        assert await paginator.avalidate_number(1.0) == 1

    async def test_no_content_allow_empty_first_page(self):
        # With no content and allow_empty_first_page=True, 1 is a valid page number
        paginator = AsyncPaginator([], 2)
        assert await paginator.avalidate_number(1) == 1

    async def test_paginate_misc_classes(self):
        class CountContainer:
            async def acount(self):
                return 42

        # Paginator can be passed other objects with a count() method.
        paginator = AsyncPaginator(CountContainer(), 10)
        assert 42 == await paginator.acount()
        assert 5 == await paginator.anum_pages()
        assert [1, 2, 3, 4, 5] == list(await paginator.apage_range())

        # AsyncPaginator can be passed other objects that implement __len__.
        class LenContainer:
            def __len__(self):
                return 42

        paginator = AsyncPaginator(LenContainer(), 10)
        assert 42 == await paginator.acount()
        assert 5 == await paginator.anum_pages()
        assert [1, 2, 3, 4, 5] == list(await paginator.apage_range())

    async def test_count_does_not_silence_attribute_error(self):
        class AttributeErrorContainer:
            async def acount(self):
                raise AttributeError("abc")

        with pytest.raises(AttributeError, match="abc"):
            await AsyncPaginator(AttributeErrorContainer(), 10).acount()

    async def test_count_does_not_silence_type_error(self):
        class TypeErrorContainer:
            async def acount(self):
                raise TypeError("abc")

        with pytest.raises(TypeError, match="abc"):
            await AsyncPaginator(TypeErrorContainer(), 10).acount()

    async def check_indexes(self, params, page_num, indexes):
        """
        Helper method that instantiates a AsyncPaginator object from the passed
        params and then checks that the start and end indexes of the passed
        page_num match those given as a 2-tuple in indexes.
        """
        paginator = AsyncPaginator(*params)
        if page_num == "first":
            page_num = 1
        elif page_num == "last":
            page_num = await paginator.anum_pages()
        page = await paginator.apage(page_num)
        start, end = indexes
        msg = (
            "For %s of page %s, expected %s but got %s. "
            "AsyncPaginator parameters were: %s"
        )
        assert start == await page.astart_index(), msg % (
            "start index",
            page_num,
            start,
            await page.astart_index(),
            params,
        )
        assert end == await page.aend_index(), msg % (
            "end index",
            page_num,
            end,
            await page.aend_index(),
            params,
        )

    async def test_page_indexes(self):
        """
        AsyncPaginator pages have the correct start and end indexes.
        """
        ten = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        tests = (
            # Each item is 3-tuple:
            #     First tuple is AsyncPaginator parameters - object_list, per_page,
            #         orphans, and allow_empty_first_page.
            #     Second tuple is the start and end indexes of the first page.
            #     Third tuple is the start and end indexes of the last page.
            # Ten items, varying per_page, no orphans.
            ((ten, 1, 0, True), (1, 1), (10, 10)),
            ((ten, 2, 0, True), (1, 2), (9, 10)),
            ((ten, 3, 0, True), (1, 3), (10, 10)),
            ((ten, 5, 0, True), (1, 5), (6, 10)),
            # Ten items, varying per_page, with orphans.
            ((ten, 1, 1, True), (1, 1), (9, 10)),
            ((ten, 1, 2, True), (1, 1), (8, 10)),
            ((ten, 3, 1, True), (1, 3), (7, 10)),
            ((ten, 3, 2, True), (1, 3), (7, 10)),
            ((ten, 3, 4, True), (1, 3), (4, 10)),
            ((ten, 5, 1, True), (1, 5), (6, 10)),
            ((ten, 5, 2, True), (1, 5), (6, 10)),
            ((ten, 5, 5, True), (1, 10), (1, 10)),
            # One item, varying orphans, no empty first page.
            (([1], 4, 0, False), (1, 1), (1, 1)),
            (([1], 4, 1, False), (1, 1), (1, 1)),
            (([1], 4, 2, False), (1, 1), (1, 1)),
            # One item, varying orphans, allow empty first page.
            (([1], 4, 0, True), (1, 1), (1, 1)),
            (([1], 4, 1, True), (1, 1), (1, 1)),
            (([1], 4, 2, True), (1, 1), (1, 1)),
            # Zero items, varying orphans, allow empty first page.
            (([], 4, 0, True), (0, 0), (0, 0)),
            (([], 4, 1, True), (0, 0), (0, 0)),
            (([], 4, 2, True), (0, 0), (0, 0)),
        )
        for params, first, last in tests:
            await self.check_indexes(params, "first", first)
            await self.check_indexes(params, "last", last)

        # When no items and no empty first page, we should get EmptyPage error.
        with pytest.raises(EmptyPage):
            await self.check_indexes(([], 4, 0, False), 1, None)
        with pytest.raises(EmptyPage):
            await self.check_indexes(([], 4, 1, False), 1, None)
        with pytest.raises(EmptyPage):
            await self.check_indexes(([], 4, 2, False), 1, None)

    async def test_page_sequence(self):
        """
        A paginator page acts like a standard sequence.
        """
        eleven = "abcdefghijk"
        page2 = await AsyncPaginator(eleven, per_page=5, orphans=1).apage(2)
        assert await page2.alen() == 6
        assert "k" in await page2.alist()
        assert "a" not in await page2.alist()
        assert "".join(await page2.alist()) == "fghijk"
        assert "".join(reversed(await page2.alist())) == "kjihgf"

    async def test_get_page_hook(self):
        """
        A AsyncPaginator subclass can use the ``_get_page`` hook to
        return an alternative to the standard Page class.
        """
        eleven = "abcdefghijk"
        paginator = AsyncValidAdjacentNumsPaginator(eleven, per_page=6)
        page1 = await paginator.apage(1)
        page2 = await paginator.apage(2)
        assert await page1.aprevious_page_number() is None
        assert await page1.anext_page_number() == 2
        assert await page2.aprevious_page_number() == 1
        assert await page2.anext_page_number() is None

    async def test_page_range_iterator(self):
        """
        AsyncPaginator.page_range should be an iterator.
        """
        assert isinstance(
            await AsyncPaginator([1, 2, 3], 2).apage_range(), type(range(0))
        )

    async def test_get_page(self):
        """
        AsyncPaginator.get_page() returns a valid page even with invalid page
        arguments.
        """
        paginator = AsyncPaginator([1, 2, 3], 2)
        page = await paginator.aget_page(1)
        assert page.number == 1
        assert page.object_list == [1, 2]
        # An empty page returns the last page.
        page = await paginator.aget_page(3)
        assert page.number == 2
        # Non-integer page returns the first page.
        page = await paginator.aget_page(None)
        assert page.number == 1

    async def test_get_page_empty_object_list(self):
        """AsyncPaginator.get_page() with an empty object_list."""
        paginator = AsyncPaginator([], 2)
        # An empty page returns the last page.
        page = await paginator.aget_page(1)
        assert page.number == 1
        page = await paginator.aget_page(2)
        assert page.number == 1
        # Non-integer page returns the first page.
        page = await paginator.aget_page(None)
        assert page.number == 1

    async def test_get_page_empty_object_list_and_allow_empty_first_page_false(self):
        """
        AsyncPaginator.get_page() raises EmptyPage if allow_empty_first_page=False
        and object_list is empty.
        """
        paginator = AsyncPaginator([], 2, allow_empty_first_page=False)
        with pytest.raises(EmptyPage):
            await paginator.aget_page(1)

    async def test_paginator_iteration(self, subtests):
        paginator = AsyncPaginator([1, 2, 3], 2)
        page_iterator = aiter(paginator)
        for page, expected in enumerate(([1, 2], [3]), start=1):
            with subtests.test(page=page):
                assert expected == await (await anext(page_iterator)).alist()

        assert [str(page) async for page in aiter(paginator)], [
            "<Page 1 of 2>",
            "<Page 2 of 2>",
        ]

    async def test_page_getitem(self):
        paginator = AsyncPaginator([1, 2, 3], 2)
        page = await paginator.apage(1)
        assert await page.agetitem(0) == 1

    async def test_page_iteration_with_list(self):
        paginator = AsyncPaginator([1, 2, 3, 4], 1)
        page = await paginator.aget_page(1)
        assert len([item async for item in page]) == 1
        paginator = AsyncPaginator([1, 2, 3, 4], 3)
        page = await paginator.aget_page(1)
        assert len([item async for item in page]) == 3

    async def test_get_elided_page_range(self, mocker, subtests):
        # AsyncPaginator.avalidate_number() must be called:
        paginator = AsyncPaginator([1, 2, 3], 2)
        mock = mocker.patch.object(paginator, "avalidate_number")
        mock.assert_not_called()
        [item async for item in paginator.aget_elided_page_range(2)]
        mock.assert_called_with(2)

        ELLIPSIS = AsyncPaginator.ELLIPSIS

        # Range is not elided if not enough pages when using default arguments:
        paginator = AsyncPaginator(range(10 * 100), 100)
        page_range = paginator.aget_elided_page_range(1)
        assert isinstance(page_range, collections.abc.AsyncGenerator)
        assert ELLIPSIS not in [page async for page in page_range]
        paginator = AsyncPaginator(range(10 * 100 + 1), 100)
        assert isinstance(page_range, collections.abc.AsyncGenerator)
        page_range = paginator.aget_elided_page_range(1)
        assert ELLIPSIS in [page async for page in page_range]

        # Range should be elided if enough pages when using default arguments:
        tests = [
            # on_each_side=3, on_ends=2
            (1, [1, 2, 3, 4, ELLIPSIS, 49, 50]),
            (6, [1, 2, 3, 4, 5, 6, 7, 8, 9, ELLIPSIS, 49, 50]),
            (7, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, ELLIPSIS, 49, 50]),
            (8, [1, 2, ELLIPSIS, 5, 6, 7, 8, 9, 10, 11, ELLIPSIS, 49, 50]),
            (43, [1, 2, ELLIPSIS, 40, 41, 42, 43, 44, 45, 46, ELLIPSIS, 49, 50]),
            (44, [1, 2, ELLIPSIS, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50]),
            (45, [1, 2, ELLIPSIS, 42, 43, 44, 45, 46, 47, 48, 49, 50]),
            (50, [1, 2, ELLIPSIS, 47, 48, 49, 50]),
        ]
        paginator = AsyncPaginator(range(5000), 100)
        for number, expected in tests:
            with subtests.test(number=number):
                page_range = paginator.aget_elided_page_range(number)
                assert isinstance(page_range, collections.abc.AsyncGenerator)
                assert [page async for page in page_range] == expected

        # Range is not elided if not enough pages when using custom arguments:
        tests = [
            (6, 2, 1, 1),
            (8, 1, 3, 1),
            (8, 4, 0, 1),
            (4, 1, 1, 1),
            # When on_each_side and on_ends are both <= 1 but not both == 1 it
            # is a special case where the range is not elided until an extra
            # page is added.
            (2, 0, 1, 2),
            (2, 1, 0, 2),
            (1, 0, 0, 2),
        ]
        for pages, on_each_side, on_ends, elided_after in tests:
            for offset in range(elided_after + 1):
                with subtests.test(
                    pages=pages,
                    offset=elided_after,
                    on_each_side=on_each_side,
                    on_ends=on_ends,
                ):
                    paginator = AsyncPaginator(range((pages + offset) * 100), 100)
                    page_range = paginator.aget_elided_page_range(
                        1,
                        on_each_side=on_each_side,
                        on_ends=on_ends,
                    )
                    assert isinstance(page_range, collections.abc.AsyncGenerator)
                    if offset < elided_after:
                        assert ELLIPSIS not in [page async for page in page_range]
                    else:
                        assert ELLIPSIS in [page async for page in page_range]

        # Range should be elided if enough pages when using custom arguments:
        tests = [
            # on_each_side=2, on_ends=1
            (1, 2, 1, [1, 2, 3, ELLIPSIS, 50]),
            (4, 2, 1, [1, 2, 3, 4, 5, 6, ELLIPSIS, 50]),
            (5, 2, 1, [1, 2, 3, 4, 5, 6, 7, ELLIPSIS, 50]),
            (6, 2, 1, [1, ELLIPSIS, 4, 5, 6, 7, 8, ELLIPSIS, 50]),
            (45, 2, 1, [1, ELLIPSIS, 43, 44, 45, 46, 47, ELLIPSIS, 50]),
            (46, 2, 1, [1, ELLIPSIS, 44, 45, 46, 47, 48, 49, 50]),
            (47, 2, 1, [1, ELLIPSIS, 45, 46, 47, 48, 49, 50]),
            (50, 2, 1, [1, ELLIPSIS, 48, 49, 50]),
            # on_each_side=1, on_ends=3
            (1, 1, 3, [1, 2, ELLIPSIS, 48, 49, 50]),
            (5, 1, 3, [1, 2, 3, 4, 5, 6, ELLIPSIS, 48, 49, 50]),
            (6, 1, 3, [1, 2, 3, 4, 5, 6, 7, ELLIPSIS, 48, 49, 50]),
            (7, 1, 3, [1, 2, 3, ELLIPSIS, 6, 7, 8, ELLIPSIS, 48, 49, 50]),
            (44, 1, 3, [1, 2, 3, ELLIPSIS, 43, 44, 45, ELLIPSIS, 48, 49, 50]),
            (45, 1, 3, [1, 2, 3, ELLIPSIS, 44, 45, 46, 47, 48, 49, 50]),
            (46, 1, 3, [1, 2, 3, ELLIPSIS, 45, 46, 47, 48, 49, 50]),
            (50, 1, 3, [1, 2, 3, ELLIPSIS, 49, 50]),
            # on_each_side=4, on_ends=0
            (1, 4, 0, [1, 2, 3, 4, 5, ELLIPSIS]),
            (5, 4, 0, [1, 2, 3, 4, 5, 6, 7, 8, 9, ELLIPSIS]),
            (6, 4, 0, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, ELLIPSIS]),
            (7, 4, 0, [ELLIPSIS, 3, 4, 5, 6, 7, 8, 9, 10, 11, ELLIPSIS]),
            (44, 4, 0, [ELLIPSIS, 40, 41, 42, 43, 44, 45, 46, 47, 48, ELLIPSIS]),
            (45, 4, 0, [ELLIPSIS, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50]),
            (46, 4, 0, [ELLIPSIS, 42, 43, 44, 45, 46, 47, 48, 49, 50]),
            (50, 4, 0, [ELLIPSIS, 46, 47, 48, 49, 50]),
            # on_each_side=0, on_ends=1
            (1, 0, 1, [1, ELLIPSIS, 50]),
            (2, 0, 1, [1, 2, ELLIPSIS, 50]),
            (3, 0, 1, [1, 2, 3, ELLIPSIS, 50]),
            (4, 0, 1, [1, ELLIPSIS, 4, ELLIPSIS, 50]),
            (47, 0, 1, [1, ELLIPSIS, 47, ELLIPSIS, 50]),
            (48, 0, 1, [1, ELLIPSIS, 48, 49, 50]),
            (49, 0, 1, [1, ELLIPSIS, 49, 50]),
            (50, 0, 1, [1, ELLIPSIS, 50]),
            # on_each_side=0, on_ends=0
            (1, 0, 0, [1, ELLIPSIS]),
            (2, 0, 0, [1, 2, ELLIPSIS]),
            (3, 0, 0, [ELLIPSIS, 3, ELLIPSIS]),
            (48, 0, 0, [ELLIPSIS, 48, ELLIPSIS]),
            (49, 0, 0, [ELLIPSIS, 49, 50]),
            (50, 0, 0, [ELLIPSIS, 50]),
        ]
        paginator = AsyncPaginator(range(5000), 100)
        for number, on_each_side, on_ends, expected in tests:
            with subtests.test(
                number=number, on_each_side=on_each_side, on_ends=on_ends
            ):
                page_range = paginator.aget_elided_page_range(
                    number,
                    on_each_side=on_each_side,
                    on_ends=on_ends,
                )
                assert isinstance(page_range, collections.abc.AsyncGenerator)
                assert [page async for page in page_range] == expected


@pytest.mark.django_db(transaction=True)
class TestModelPagination:
    """
    Test pagination with Django model instances
    """

    @pytest.fixture(autouse=True)
    async def setup(self):
        # Prepare a list of objects for pagination.
        pub_date = datetime(2005, 7, 29)
        self.articles = [
            await Article.objects.acreate(headline=f"Article {x}", pub_date=pub_date)
            for x in range(1, 10)
        ]

    async def test_first_page(self):
        paginator = AsyncPaginator(Article.objects.order_by("id"), 5)
        p = await paginator.apage(1)
        assert "<Async Page 1>" == str(p)
        assert [o async for o in p.object_list] == self.articles[:5]
        assert await p.ahas_next()
        assert await p.ahas_previous() is False
        assert await p.ahas_other_pages()
        assert 2 == await p.anext_page_number()
        with pytest.raises(InvalidPage):
            await p.aprevious_page_number()
        assert 1 == await p.astart_index()
        assert 5 == await p.aend_index()

    async def test_last_page(self):
        paginator = AsyncPaginator(Article.objects.order_by("id"), 5)
        p = await paginator.apage(2)
        assert "<Async Page 2>" == str(p)
        assert [o async for o in p.object_list] == self.articles[5:]
        assert await p.ahas_next() is False
        assert await p.ahas_previous()
        assert await p.ahas_other_pages()
        with pytest.raises(InvalidPage):
            await p.anext_page_number()
        assert 1 == await p.aprevious_page_number()
        assert 6 == await p.astart_index()
        assert 9 == await p.aend_index()

    async def test_page_getitem(self):
        """
        Tests proper behavior of a paginator page __getitem__ (queryset
        evaluation, slicing, exception raised).
        """
        paginator = AsyncPaginator(Article.objects.order_by("id"), 5)
        p = await paginator.apage(1)

        # object_list queryset is not evaluated by an invalid __getitem__ call.
        # (this happens from the template engine when using e.g.:
        # {% page_obj.has_previous %}).
        assert p.object_list._result_cache is None
        msg = "Page indices must be integers or slices, not str."
        with pytest.raises(TypeError, match=msg):
            await p.agetitem("has_previous")
        assert p.object_list._result_cache is None
        assert not isinstance(p.object_list, list)

        # Make sure slicing the Page object with numbers and slice objects work.
        assert await p.agetitem(0) == self.articles[0]
        assert await p.agetitem(0) == self.articles[0]
        assert await p.agetitem(slice(2)) == self.articles[:2]
        # After __getitem__ is called, object_list is a list
        assert isinstance(p.object_list, list)

    def test_paginating_unordered_queryset_raises_warning(self):
        msg = (
            "Pagination may yield inconsistent results with an unordered "
            "object_list: <class 'test_pagination.models.Article'> QuerySet."
        )
        with assertWarnsMessage(UnorderedObjectListWarning, msg):
            AsyncPaginator(Article.objects.all(), 5)
        # The warning points at the AsyncPaginator caller (i.e. the stacklevel
        # is appropriate).
        # assert cm.filename == __file__

    def test_paginating_empty_queryset_does_not_warn(self):
        with warnings.catch_warnings(record=True) as recorded:
            AsyncPaginator(Article.objects.none(), 5)
        assert len(recorded) == 0

    def test_paginating_unordered_object_list_raises_warning(self):
        """
        Unordered object list warning with an object that has an ordered
        attribute but not a model attribute.
        """

        class ObjectList:
            ordered = False

        object_list = ObjectList()
        msg = (
            "Pagination may yield inconsistent results with an unordered "
            "object_list: {!r}.".format(object_list)
        )
        with assertWarnsMessage(UnorderedObjectListWarning, msg):
            AsyncPaginator(object_list, 5)

    async def test_page_iteration_with_queryset(self):
        paginator = AsyncPaginator(Article.objects.all(), 1)
        page = await paginator.aget_page(1)
        assert len([item async for item in page]) == 1
        paginator = AsyncPaginator(Article.objects.all(), 3)
        page = await paginator.aget_page(1)
        assert len([item async for item in page]) == 3

    async def test_page_sequence_with_queryset(self):
        """
        A paginator page acts like a standard sequence.
        """
        page2 = await AsyncPaginator(
            Article.objects.all(), per_page=5, orphans=1
        ).apage(2)
        assert await page2.alen() == 4
        assert await Article.objects.aget(headline="Article 6") in await page2.alist()
        assert (
            await Article.objects.aget(headline="Article 1") not in await page2.alist()
        )
