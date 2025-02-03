from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.decorators.cache import cache_page

from django_async_extensions.aviews.generic import AsyncTemplateView

from . import views

urlpatterns = [
    # AsyncTemplateView
    path("template/no_template/", AsyncTemplateView.as_view()),
    path("template/login_required/", login_required(AsyncTemplateView.as_view())),
    path(
        "template/simple/<foo>/",
        AsyncTemplateView.as_view(template_name="generic_views/about.html"),
    ),
    path(
        "template/custom/<foo>/",
        views.CustomTemplateView.as_view(template_name="generic_views/about.html"),
    ),
    path(
        "template/content_type/",
        AsyncTemplateView.as_view(
            template_name="generic_views/robots.txt", content_type="text/plain"
        ),
    ),
    path(
        "template/cached/<foo>/",
        cache_page(2)(
            AsyncTemplateView.as_view(template_name="generic_views/about.html")
        ),
    ),
    path(
        "template/extra_context/",
        AsyncTemplateView.as_view(
            template_name="generic_views/about.html", extra_context={"title": "Title"}
        ),
    ),
    # Useful for testing redirects
    path("accounts/login/", auth_views.LoginView.as_view()),
    # path("BaseDateListViewTest/", dates.BaseDateListView.as_view()),
]
