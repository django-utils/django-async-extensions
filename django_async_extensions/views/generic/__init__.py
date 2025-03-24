from django_async_extensions.views.generic.base import (
    AsyncView,
    AsyncTemplateView,
    AsyncRedirectView,
)
from django_async_extensions.views.generic.dates import (
    AsyncArchiveIndexView,
    AsyncDateDetailView,
    AsyncDayArchiveView,
    AsyncMonthArchiveView,
    AsyncTodayArchiveView,
    AsyncWeekArchiveView,
    AsyncYearArchiveView,
)
from django_async_extensions.views.generic.detail import AsyncDetailView
from django_async_extensions.views.generic.edit import (
    AsyncCreateView,
    AsyncDeleteView,
    AsyncFormView,
    AsyncUpdateView,
)
from django_async_extensions.views.generic.list import AsyncListView


__all__ = [
    "AsyncView",
    "AsyncTemplateView",
    "AsyncRedirectView",
    "AsyncArchiveIndexView",
    "AsyncYearArchiveView",
    "AsyncMonthArchiveView",
    "AsyncWeekArchiveView",
    "AsyncDayArchiveView",
    "AsyncTodayArchiveView",
    "AsyncDateDetailView",
    "AsyncDetailView",
    "AsyncFormView",
    "AsyncCreateView",
    "AsyncDeleteView",
    "AsyncListView",
    "AsyncUpdateView",
]
