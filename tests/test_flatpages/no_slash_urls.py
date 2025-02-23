from django.urls import include, path

urlpatterns = [
    path("flatpage", include("django_async_extensions.acontrib.flatpages.urls")),
]
