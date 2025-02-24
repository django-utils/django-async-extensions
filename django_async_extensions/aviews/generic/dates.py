import datetime

from django.conf import settings
from django.db import models
from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic.dates import (
    timezone_today,
    _date_from_string,
    YearMixin,
    MonthMixin,
    WeekMixin,
    DayMixin,
    DateMixin,
)

from django_async_extensions.aviews.generic.base import AsyncView
from django_async_extensions.aviews.generic.detail import (
    AsyncBaseDetailView,
    AsyncSingleObjectTemplateResponseMixin,
)
from django_async_extensions.aviews.generic.list import (
    AsyncMultipleObjectMixin,
    AsyncMultipleObjectTemplateResponseMixin,
)


class AsyncYearMixin(YearMixin):
    async def get_next_year(self, date):
        return await _get_next_prev(self, date, is_previous=False, period="year")

    async def get_previous_year(self, date):
        return await _get_next_prev(self, date, is_previous=True, period="year")


class AsyncMonthMixin(MonthMixin):
    async def get_next_month(self, date):
        return await _get_next_prev(self, date, is_previous=False, period="month")

    async def get_previous_month(self, date):
        return await _get_next_prev(self, date, is_previous=True, period="month")


class AsyncDayMixin(DayMixin):
    async def get_next_day(self, date):
        return await _get_next_prev(self, date, is_previous=False, period="day")

    async def get_previous_day(self, date):
        return await _get_next_prev(self, date, is_previous=True, period="day")


class AsyncWeekMixin(WeekMixin):
    async def get_next_week(self, date):
        return await _get_next_prev(self, date, is_previous=False, period="week")

    async def get_previous_week(self, date):
        return await _get_next_prev(self, date, is_previous=True, period="week")


class AsyncDateMixin(DateMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_uses_datetime = None

    async def uses_datetime_field(self):
        """
        Return `True` if the date field is a `DateTimeField` and `False`
        if it's a `DateField`.
        """
        if self._cached_uses_datetime is not None:
            return self._cached_uses_datetime
        qs = await self.get_queryset()
        model = qs.model if self.model is None else self.model
        field = model._meta.get_field(self.get_date_field())
        self._cached_uses_datetime = isinstance(field, models.DateTimeField)
        return self._cached_uses_datetime


class AsyncBaseDateListView(AsyncMultipleObjectMixin, AsyncDateMixin, AsyncView):
    """Abstract base class for date-based views displaying a list of objects."""

    allow_empty = False
    date_list_period = "year"

    async def get(self, request, *args, **kwargs):
        self.date_list, self.object_list, extra_context = await self.get_dated_items()
        context = await self.get_context_data(
            object_list=self.object_list, date_list=self.date_list, **extra_context
        )
        return await self.render_to_response(context)

    async def get_dated_items(self):
        raise NotImplementedError(
            "An AsyncDateView must provide an implementation of get_dated_items()"
        )

    def get_ordering(self):
        """
        Return the field or fields to use for ordering the queryset; use the
        date field by default.
        """
        return "-%s" % self.get_date_field() if self.ordering is None else self.ordering

    async def get_dated_queryset(self, **lookup):
        """
        Get a queryset properly filtered according to `allow_future` and any
        extra lookup kwargs.
        """
        query_set = await self.get_queryset()
        qs = query_set.filter(**lookup)
        date_field = self.get_date_field()
        allow_future = self.get_allow_future()
        allow_empty = self.get_allow_empty()
        paginate_by = self.get_paginate_by(qs)

        if not allow_future:
            now = (
                timezone.now() if await self.uses_datetime_field() else timezone_today()
            )
            qs = qs.filter(**{"%s__lte" % date_field: now})

        if not allow_empty:
            # When pagination is enabled, it's better to do a cheap query
            # than to load the unpaginated queryset in memory.
            is_empty = (
                not [i async for i in qs]
                if paginate_by is None
                else not await qs.aexists()
            )
            if is_empty:
                raise Http404(
                    _("No %(verbose_name_plural)s available")
                    % {
                        "verbose_name_plural": qs.model._meta.verbose_name_plural,
                    }
                )

        return qs

    def get_date_list_period(self):
        """
        Get the aggregation period for the list of dates: 'year', 'month', or
        'day'.
        """
        return self.date_list_period

    async def get_date_list(self, queryset, date_type=None, ordering="ASC"):
        """
        Get a date list by calling `queryset.dates/datetimes()`, checking
        along the way for empty lists that aren't allowed.
        """
        date_field = self.get_date_field()
        allow_empty = self.get_allow_empty()
        if date_type is None:
            date_type = self.get_date_list_period()

        if await self.uses_datetime_field():
            date_list = queryset.datetimes(date_field, date_type, ordering)
        else:
            date_list = queryset.dates(date_field, date_type, ordering)

        check_date_list = [item async for item in date_list]
        if check_date_list is not None and not check_date_list and not allow_empty:
            raise Http404(
                _("No %(verbose_name_plural)s available")
                % {
                    "verbose_name_plural": queryset.model._meta.verbose_name_plural,
                }
            )

        return date_list


class AsyncBaseArchiveIndexView(AsyncBaseDateListView):
    """
    Base view for archives of date-based items.

    This requires subclassing to provide a response mixin.
    """

    context_object_name = "latest"

    async def get_dated_items(self):
        """Return (date_list, items, extra_context) for this request."""
        qs = await self.get_dated_queryset()
        date_list = await self.get_date_list(qs, ordering="DESC")

        if not date_list:
            qs = qs.none()

        return (date_list, qs, {})


class AsyncArchiveIndexView(
    AsyncMultipleObjectTemplateResponseMixin, AsyncBaseArchiveIndexView
):
    """Top-level archive of date-based items."""

    template_name_suffix = "_archive"


class AsyncBaseYearArchiveView(AsyncYearMixin, AsyncBaseDateListView):
    """List of objects published in a given year."""

    date_list_period = "month"
    make_object_list = False

    async def get_dated_items(self):
        """Return (date_list, items, extra_context) for this request."""
        year = self.get_year()

        date_field = self.get_date_field()
        date = _date_from_string(year, self.get_year_format())

        since = self._make_date_lookup_arg(date)
        until = self._make_date_lookup_arg(self._get_next_year(date))
        lookup_kwargs = {
            "%s__gte" % date_field: since,
            "%s__lt" % date_field: until,
        }

        qs = await self.get_dated_queryset(**lookup_kwargs)
        date_list = await self.get_date_list(qs)

        if not self.get_make_object_list():
            # We need this to be a queryset since parent classes introspect it
            # to find information about the model.
            qs = qs.none()

        return (
            date_list,
            qs,
            {
                "year": date,
                "next_year": await self.get_next_year(date),
                "previous_year": await self.get_previous_year(date),
            },
        )

    def get_make_object_list(self):
        """
        Return `True` if this view should contain the full list of objects in
        the given year.
        """
        return self.make_object_list


class AsyncYearArchiveView(
    AsyncMultipleObjectTemplateResponseMixin, AsyncBaseYearArchiveView
):
    """List of objects published in a given year."""

    template_name_suffix = "_archive_year"


class AsyncBaseMonthArchiveView(AsyncYearMixin, AsyncMonthMixin, AsyncBaseDateListView):
    """List of objects published in a given month."""

    date_list_period = "day"

    async def get_dated_items(self):
        """Return (date_list, items, extra_context) for this request."""
        year = self.get_year()
        month = self.get_month()

        date_field = self.get_date_field()
        date = _date_from_string(
            year, self.get_year_format(), month, self.get_month_format()
        )

        since = self._make_date_lookup_arg(date)
        until = self._make_date_lookup_arg(self._get_next_month(date))
        lookup_kwargs = {
            "%s__gte" % date_field: since,
            "%s__lt" % date_field: until,
        }

        qs = await self.get_dated_queryset(**lookup_kwargs)
        date_list = await self.get_date_list(qs)

        return (
            date_list,
            qs,
            {
                "month": date,
                "next_month": await self.get_next_month(date),
                "previous_month": await self.get_previous_month(date),
            },
        )


class AsyncMonthArchiveView(
    AsyncMultipleObjectTemplateResponseMixin, AsyncBaseMonthArchiveView
):
    """List of objects published in a given month."""

    template_name_suffix = "_archive_month"


class AsyncBaseWeekArchiveView(AsyncYearMixin, AsyncWeekMixin, AsyncBaseDateListView):
    """List of objects published in a given week."""

    async def get_dated_items(self):
        """Return (date_list, items, extra_context) for this request."""
        year = self.get_year()
        week = self.get_week()

        date_field = self.get_date_field()
        week_format = self.get_week_format()
        week_choices = {"%W": "1", "%U": "0", "%V": "1"}
        try:
            week_start = week_choices[week_format]
        except KeyError:
            raise ValueError(
                "Unknown week format %r. Choices are: %s"
                % (
                    week_format,
                    ", ".join(sorted(week_choices)),
                )
            )
        year_format = self.get_year_format()
        if week_format == "%V" and year_format != "%G":
            raise ValueError(
                "ISO week directive '%s' is incompatible with the year "
                "directive '%s'. Use the ISO year '%%G' instead."
                % (
                    week_format,
                    year_format,
                )
            )
        date = _date_from_string(year, year_format, week_start, "%w", week, week_format)
        since = self._make_date_lookup_arg(date)
        until = self._make_date_lookup_arg(self._get_next_week(date))
        lookup_kwargs = {
            "%s__gte" % date_field: since,
            "%s__lt" % date_field: until,
        }

        qs = await self.get_dated_queryset(**lookup_kwargs)

        return (
            None,
            qs,
            {
                "week": date,
                "next_week": await self.get_next_week(date),
                "previous_week": await self.get_previous_week(date),
            },
        )


class AsyncWeekArchiveView(
    AsyncMultipleObjectTemplateResponseMixin, AsyncBaseWeekArchiveView
):
    """List of objects published in a given week."""

    template_name_suffix = "_archive_week"


class AsyncBaseDayArchiveView(
    AsyncYearMixin, AsyncMonthMixin, AsyncDayMixin, AsyncBaseDateListView
):
    """List of objects published on a given day."""

    async def get_dated_items(self):
        """Return (date_list, items, extra_context) for this request."""
        year = self.get_year()
        month = self.get_month()
        day = self.get_day()

        date = _date_from_string(
            year,
            self.get_year_format(),
            month,
            self.get_month_format(),
            day,
            self.get_day_format(),
        )

        return await self._get_dated_items(date)

    async def _get_dated_items(self, date):
        """
        Do the actual heavy lifting of getting the dated items; this accepts a
        date object so that TodayArchiveView can be trivial.
        """
        lookup_kwargs = self._make_single_date_lookup(date)
        qs = await self.get_dated_queryset(**lookup_kwargs)

        return (
            None,
            qs,
            {
                "day": date,
                "previous_day": await self.get_previous_day(date),
                "next_day": await self.get_next_day(date),
                "previous_month": await self.get_previous_month(date),
                "next_month": await self.get_next_month(date),
            },
        )


class AsyncDayArchiveView(
    AsyncMultipleObjectTemplateResponseMixin, AsyncBaseDayArchiveView
):
    """List of objects published on a given day."""

    template_name_suffix = "_archive_day"


class AsyncBaseTodayArchiveView(AsyncBaseDayArchiveView):
    """List of objects published today."""

    async def get_dated_items(self):
        """Return (date_list, items, extra_context) for this request."""
        return await self._get_dated_items(datetime.date.today())


class AsyncTodayArchiveView(
    AsyncMultipleObjectTemplateResponseMixin, AsyncBaseTodayArchiveView
):
    """List of objects published today."""

    template_name_suffix = "_archive_day"


class AsyncBaseDateDetailView(
    AsyncYearMixin, AsyncMonthMixin, AsyncDayMixin, AsyncDateMixin, AsyncBaseDetailView
):
    """
    Detail view of a single object on a single date; this differs from the
    standard DetailView by accepting a year/month/day in the URL.
    """

    async def get_object(self, queryset=None):
        """Get the object this request displays."""
        year = self.get_year()
        month = self.get_month()
        day = self.get_day()
        date = _date_from_string(
            year,
            self.get_year_format(),
            month,
            self.get_month_format(),
            day,
            self.get_day_format(),
        )

        # Use a custom queryset if provided
        qs = await self.get_queryset() if queryset is None else queryset

        if not self.get_allow_future() and date > datetime.date.today():
            raise Http404(
                _(
                    "Future %(verbose_name_plural)s not available because "
                    "%(class_name)s.allow_future is False."
                )
                % {
                    "verbose_name_plural": qs.model._meta.verbose_name_plural,
                    "class_name": self.__class__.__name__,
                }
            )

        # Filter down a queryset from self.queryset using the date from the
        # URL. This'll get passed as the queryset to DetailView.get_object,
        # which'll handle the 404
        lookup_kwargs = self._make_single_date_lookup(date)
        qs = qs.filter(**lookup_kwargs)

        return await super().get_object(queryset=qs)


class AsyncDateDetailView(
    AsyncSingleObjectTemplateResponseMixin, AsyncBaseDateDetailView
):
    """
    Detail view of a single object on a single date; this differs from the
    standard DetailView by accepting a year/month/day in the URL.
    """

    template_name_suffix = "_detail"


async def _get_next_prev(generic_view, date, is_previous, period):
    """
    Get the next or the previous valid date. The idea is to allow links on
    month/day views to never be 404s by never providing a date that'll be
    invalid for the given view.

    This is a bit complicated since it handles different intervals of time,
    hence the coupling to generic_view.

    However in essence the logic comes down to:

        * If allow_empty and allow_future are both true, this is easy: just
          return the naive result (just the next/previous day/week/month,
          regardless of object existence.)

        * If allow_empty is true, allow_future is false, and the naive result
          isn't in the future, then return it; otherwise return None.

        * If allow_empty is false and allow_future is true, return the next
          date *that contains a valid object*, even if it's in the future. If
          there are no next objects, return None.

        * If allow_empty is false and allow_future is false, return the next
          date that contains a valid object. If that date is in the future, or
          if there are no next objects, return None.
    """
    date_field = generic_view.get_date_field()
    allow_empty = generic_view.get_allow_empty()
    allow_future = generic_view.get_allow_future()

    get_current = getattr(generic_view, "_get_current_%s" % period)
    get_next = getattr(generic_view, "_get_next_%s" % period)

    # Bounds of the current interval
    start, end = get_current(date), get_next(date)

    # If allow_empty is True, the naive result will be valid
    if allow_empty:
        if is_previous:
            result = get_current(start - datetime.timedelta(days=1))
        else:
            result = end

        if allow_future or result <= timezone_today():
            return result
        else:
            return None

    # Otherwise, we'll need to go to the database to look for an object
    # whose date_field is at least (greater than/less than) the given
    # naive result
    else:
        # Construct a lookup and an ordering depending on whether we're doing
        # a previous date or a next date lookup.
        if is_previous:
            lookup = {"%s__lt" % date_field: generic_view._make_date_lookup_arg(start)}
            ordering = "-%s" % date_field
        else:
            lookup = {"%s__gte" % date_field: generic_view._make_date_lookup_arg(end)}
            ordering = date_field

        # Filter out objects in the future if appropriate.
        if not allow_future:
            # Fortunately, to match the implementation of allow_future,
            # we need __lte, which doesn't conflict with __lt above.
            if generic_view.uses_datetime_field:
                now = timezone.now()
            else:
                now = timezone_today()
            lookup["%s__lte" % date_field] = now

        queryset = await generic_view.get_queryset()
        qs = queryset.filter(**lookup).order_by(ordering)

        # Snag the first object from the queryset; if it doesn't exist that
        # means there's no next/previous link available.
        try:
            result = getattr(await qs[0:1].aget(), date_field)
        except qs.model.DoesNotExist:
            return None

        # Convert datetimes to dates in the current time zone.
        if await generic_view.uses_datetime_field():
            if settings.USE_TZ:
                result = timezone.localtime(result)
            result = result.date()

        # Return the first day of the period.
        return get_current(result)
