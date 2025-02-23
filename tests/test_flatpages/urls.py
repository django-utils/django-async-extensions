from django.urls import include, path


urlpatterns = [
    path("flatpage_root/", include("django_async_extensions.acontrib.flatpages.urls")),
]
