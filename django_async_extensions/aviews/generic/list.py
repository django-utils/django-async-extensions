from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import InvalidPage
from django.db.models import QuerySet
from django.http import Http404
from django.utils.translation import gettext as _
from django.views.generic.list import (
    MultipleObjectMixin,
    MultipleObjectTemplateResponseMixin,
)

from django_async_extensions.acore.paginator import AsyncPaginator
from django_async_extensions.aviews.generic.base import AsyncView


class AsyncMultipleObjectMixin(MultipleObjectMixin):
    paginator_class = AsyncPaginator

    async def get_queryset(self):
        """
        Return the list of items for this view.

        The return value must be an iterable and may be an instance of
        `QuerySet` in which case `QuerySet` specific behavior will be enabled.
        """
        if self.queryset is not None:
            queryset = self.queryset
            if isinstance(queryset, QuerySet):
                queryset = queryset.all()
        elif self.model is not None:
            queryset = self.model._default_manager.all()
        else:
            raise ImproperlyConfigured(
                "%(cls)s is missing a QuerySet. Define "
                "%(cls)s.model, %(cls)s.queryset, or override "
                "%(cls)s.get_queryset()." % {"cls": self.__class__.__name__}
            )
        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)

        return queryset

    async def paginate_queryset(self, queryset, page_size):
        paginator = self.get_paginator(
            queryset,
            page_size,
            orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty(),
        )
        page_kwargs = self.page_kwarg
        page = self.kwargs.get(page_kwargs) or self.request.GET.get(page_kwargs) or 1
        try:
            page_number = int(page)
        except ValueError:
            if page == "last":
                page_number = await paginator.anum_pages()
            else:
                raise Http404(
                    _("Page is not “last”, nor can it be converted to an int.")
                )
        try:
            page = await paginator.apage(page_number)
            return paginator, page, page.object_list, await page.ahas_other_pages()
        except InvalidPage as e:
            raise Http404(
                _("Invalid page (%(page_number)s): %(message)s")
                % {"page_number": page_number, "message": str(e)}
            )

    async def get_context_data(self, *, object_list=None, **kwargs):
        """Get the context for this view."""
        queryset = object_list if object_list is not None else self.object_list
        page_size = self.get_paginate_by(queryset)
        context_object_name = self.get_context_object_name(queryset)
        if page_size:
            paginator, page, queryset, is_paginated = await self.paginate_queryset(
                queryset, page_size
            )
            context = {
                "paginator": paginator,
                "page_obj": page,
                "is_paginated": is_paginated,
                "object_list": queryset,
            }
        else:
            context = {
                "paginator": None,
                "page_obj": None,
                "is_paginated": False,
                "object_list": queryset,
            }
        if context_object_name is not None:
            context[context_object_name] = queryset
        context.update(kwargs)
        context.setdefault("view", self)
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context


class AsyncBaseListView(AsyncMultipleObjectMixin, AsyncView):
    """
    Base view for displaying a list of objects.

    This requires subclassing to provide a response mixin.
    """

    async def get(self, request, *args, **kwargs):
        self.object_list = await self.get_queryset()
        allow_empty = self.get_allow_empty()

        if not allow_empty:
            # When pagination is enabled and object_list is a queryset,
            # it's better to do a cheap query than to load the unpaginated
            # queryset in memory.
            if self.get_paginate_by(self.object_list) is not None and hasattr(
                self.object_list, "aexists"
            ):
                is_empty = not await self.object_list.aexists()
            else:
                is_empty = not [object async for object in self.object_list]
            if is_empty:
                raise Http404(
                    _("Empty list and “%(class_name)s.allow_empty” is False.")
                    % {
                        "class_name": self.__class__.__name__,
                    }
                )
        context = await self.get_context_data()
        return self.render_to_response(context)


class AsyncListView(MultipleObjectTemplateResponseMixin, AsyncBaseListView):
    """
    Render some list of objects, set by `self.model` or `self.queryset`.
    `self.queryset` can actually be any iterable of items, not just a queryset.
    """
