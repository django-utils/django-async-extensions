from django.urls import path

from django_async_extensions.acontrib.flatpages import views

urlpatterns = [
    path("flatpage/", views.flatpage, {"url": "/hardcoded/"}),
]
