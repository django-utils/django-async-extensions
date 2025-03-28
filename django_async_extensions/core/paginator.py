import inspect
from asyncio import iscoroutinefunction
from math import ceil

from asgiref.sync import sync_to_async

from django.core.exceptions import SynchronousOnlyOperation
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.utils.inspect import method_has_no_args


class AsyncPaginator(Paginator):
    def __init__(
        self,
        object_list,
        per_page,
        orphans=0,
        allow_empty_first_page=True,
        error_messages=None,
    ):
        super().__init__(
            object_list, per_page, orphans, allow_empty_first_page, error_messages
        )
        self._cache_anum_pages = None
        self._cache_acount = None

    async def __aiter__(self):
        page_range = await self.apage_range()
        for page_number in page_range:
            yield await self.apage(page_number)

    def _validate_number(self, number, num_pages):
        try:
            if isinstance(number, float) and not number.is_integer():
                raise ValueError
            number = int(number)
        except (TypeError, ValueError):
            raise PageNotAnInteger(self.error_messages["invalid_page"])
        if number < 1:
            raise EmptyPage(self.error_messages["min_page"])

        if number > num_pages:
            raise EmptyPage(self.error_messages["no_results"])
        return number

    async def avalidate_number(self, number):
        """Validate the given 1-based page number."""
        num_page = await self.anum_pages()
        return self._validate_number(number, num_page)

    async def aget_page(self, number):
        """
        Return a valid page, even if the page argument isn't a number or isn't
        in range.
        """
        try:
            number = await self.avalidate_number(number)
        except PageNotAnInteger:
            number = 1
        except EmptyPage:
            number = await self.anum_pages()
        return await self.apage(number)

    async def apage(self, number):
        """Return a AsyncPage object for the given 1-based page number."""
        number = await self.avalidate_number(number)
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        count = await self.acount()
        if top + self.orphans >= count:
            top = count
        object_list = self.object_list[bottom:top]

        return self._get_page(object_list, number, self)

    def _get_page(self, *args, **kwargs):
        """
        Return an instance of a single page.

        This hook can be used by subclasses to use an alternative to the
        standard :cls:`AsyncPage` object.
        """
        return AsyncPage(*args, **kwargs)

    async def acount(self):
        """Return the total number of objects, across all pages."""
        if self._cache_acount is not None:
            return self._cache_acount

        c = getattr(self.object_list, "acount", None)
        if (
            iscoroutinefunction(c)
            and not inspect.isbuiltin(c)
            and method_has_no_args(c)
        ):
            count = await c()
        else:
            try:
                # if somehow the `__len__` method works in a sync manner
                count = len(self.object_list)
            except SynchronousOnlyOperation:
                count = len(await sync_to_async(list)(self.object_list))

        self._cache_acount = count

        return count

    async def anum_pages(self):
        """Return the total number of pages."""
        if self._cache_anum_pages is not None:
            return self._cache_anum_pages

        count = await self.acount()
        if count == 0 and not self.allow_empty_first_page:
            self._cache_anum_pages = 0
            return self._cache_anum_pages
        hits = max(1, count - self.orphans)
        num_pages = ceil(hits / self.per_page)

        self._cache_anum_pages = num_pages

        return num_pages

    async def apage_range(self):
        """
        Return a 1-based range of pages for iterating through within
        a template for loop.
        """
        num_pages = await self.anum_pages()
        return range(1, num_pages + 1)

    async def aget_elided_page_range(self, number=1, *, on_each_side=3, on_ends=2):
        """
        Return a 1-based range of pages with some values elided.

        If the page range is larger than a given size, the whole range is not
        provided and a compact form is returned instead, e.g. for a paginator
        with 50 pages, if page 43 were the current page, the output, with the
        default arguments, would be:

            1, 2, …, 40, 41, 42, 43, 44, 45, 46, …, 49, 50.
        """
        number = await self.avalidate_number(number)
        num_pages = await self.anum_pages()
        page_range = await self.apage_range()

        for page in self._get_elided_page_range(
            number, num_pages, page_range, on_each_side, on_ends
        ):
            yield page

    def _get_elided_page_range(
        self, number, num_pages, page_range, on_each_side=3, on_ends=2
    ):
        if num_pages <= (on_each_side + on_ends) * 2:
            for page in page_range:
                yield page
            return

        if number > (1 + on_each_side + on_ends) + 1:
            for page in range(1, on_ends + 1):
                yield page
            yield self.ELLIPSIS
            for page in range(number - on_each_side, number + 1):
                yield page
        else:
            for page in range(1, number + 1):
                yield page

        if number < (num_pages - on_each_side - on_ends) - 1:
            for page in range(number + 1, number + on_each_side + 1):
                yield page
            yield self.ELLIPSIS
            for page in range(num_pages - on_ends + 1, num_pages + 1):
                yield page
        else:
            for page in range(number + 1, num_pages + 1):
                yield page


class AsyncPage:
    def __init__(self, object_list, number, paginator):
        self.object_list = object_list
        self.number = number
        self.paginator = paginator

    def __repr__(self):
        return "<Async Page %s>" % self.number

    async def __aiter__(self):
        if hasattr(self.object_list, "__aiter__"):
            async for obj in self.object_list:
                yield obj
        else:
            # this is so if object_list is actually a list, iteration doesn't fail
            for obj in self.object_list:
                yield obj

    async def _afetch_object_list(self):
        if not isinstance(self.object_list, list):
            self.object_list = await self.alist()

    async def agetitem(self, index):
        if not isinstance(index, (int, slice)):
            raise TypeError(
                "AsyncPage indices must be integers or slices, not %s."
                % type(index).__name__
            )

        # in the sync version, when `__getitem__` is called it turns the queryset
        # into a list, which errors since this is async code, so we handle that here
        await self._afetch_object_list()
        return self.object_list[index]

    async def alen(self):
        """an async interface to be used instead of `len(page)`"""
        return len(await self.alist())

    async def alist(self):
        """make a list of the items in the queryset"""
        if hasattr(self.object_list, "__aiter__"):
            return [obj async for obj in self.object_list]
        return await sync_to_async(list)(self.object_list)

    async def ahas_next(self):
        num_pages = await self.paginator.anum_pages()
        return self.number < num_pages

    async def ahas_previous(self):
        return self.number > 1

    async def ahas_other_pages(self):
        has_previous = await self.ahas_previous()
        has_next = await self.ahas_next()
        return has_previous or has_next

    async def anext_page_number(self):
        return await self.paginator.avalidate_number(self.number + 1)

    async def aprevious_page_number(self):
        return await self.paginator.avalidate_number(self.number - 1)

    async def astart_index(self):
        """
        Return the 1-based index of the first object on this page,
        relative to total objects in the paginator.
        """
        count = await self.paginator.acount()
        if count == 0:
            return 0
        return (self.paginator.per_page * (self.number - 1)) + 1

    async def aend_index(self):
        """
        Return the 1-based index of the last object on this page,
        relative to total objects found (hits).
        """
        # Special case for the last page because there can be orphans.
        num_pages = await self.paginator.anum_pages()
        if self.number == num_pages:
            return await self.paginator.acount()
        return self.number * self.paginator.per_page
