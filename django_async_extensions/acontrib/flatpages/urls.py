from django.urls import path

from django_async_extensions.acontrib.flatpages import views

urlpatterns = [
    path(
        "<path:url>",
        views.flatpage,
        name="django_async_extensions.acontrib.flatpages.views.flatpage",
    ),
]
