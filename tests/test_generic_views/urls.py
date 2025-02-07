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
        AsyncTemplateView.as_view(template_name="test_generic_views/about.html"),
    ),
    path(
        "template/custom/<foo>/",
        views.CustomTemplateView.as_view(template_name="test_generic_views/about.html"),
    ),
    path(
        "template/content_type/",
        AsyncTemplateView.as_view(
            template_name="test_generic_views/robots.txt", content_type="text/plain"
        ),
    ),
    path(
        "template/cached/<foo>/",
        cache_page(2)(
            AsyncTemplateView.as_view(template_name="test_generic_views/about.html")
        ),
    ),
    path(
        "template/extra_context/",
        AsyncTemplateView.as_view(
            template_name="test_generic_views/about.html",
            extra_context={"title": "Title"},
        ),
    ),
    # AsyncDetailView
    path("detail/obj/", views.ObjectDetail.as_view()),
    path("detail/artist/<int:pk>/", views.ArtistDetail.as_view(), name="artist_detail"),
    path("detail/author/<int:pk>/", views.AuthorDetail.as_view(), name="author_detail"),
    path(
        "detail/author/bycustompk/<foo>/",
        views.AuthorDetail.as_view(pk_url_kwarg="foo"),
    ),
    path("detail/author/byslug/<slug>/", views.AuthorDetail.as_view()),
    path(
        "detail/author/bycustomslug/<foo>/",
        views.AuthorDetail.as_view(slug_url_kwarg="foo"),
    ),
    path("detail/author/bypkignoreslug/<int:pk>-<slug>/", views.AuthorDetail.as_view()),
    path(
        "detail/author/bypkandslug/<int:pk>-<slug>/",
        views.AuthorDetail.as_view(query_pk_and_slug=True),
    ),
    path(
        "detail/author/<int:pk>/template_name_suffix/",
        views.AuthorDetail.as_view(template_name_suffix="_view"),
    ),
    path(
        "detail/author/<int:pk>/template_name/",
        views.AuthorDetail.as_view(template_name="test_generic_views/about.html"),
    ),
    path(
        "detail/author/<int:pk>/context_object_name/",
        views.AuthorDetail.as_view(context_object_name="thingy"),
    ),
    path("detail/author/<int:pk>/custom_detail/", views.AuthorCustomDetail.as_view()),
    path(
        "detail/author/<int:pk>/dupe_context_object_name/",
        views.AuthorDetail.as_view(context_object_name="object"),
    ),
    path("detail/page/<int:pk>/field/", views.PageDetail.as_view()),
    path(r"detail/author/invalid/url/", views.AuthorDetail.as_view()),
    path("detail/author/invalid/qs/", views.AuthorDetail.as_view(queryset=None)),
    path("detail/nonmodel/1/", views.NonModelDetail.as_view()),
    path("detail/doesnotexist/<pk>/", views.ObjectDoesNotExistDetail.as_view()),
    # FormView
    path("contact/", views.ContactView.as_view()),
    path("late-validation/", views.LateValidationView.as_view()),
    # ListView
    path("list/dict/", views.DictList.as_view()),
    path("list/dict/paginated/", views.DictList.as_view(paginate_by=1)),
    path("list/artists/", views.ArtistList.as_view(), name="artists_list"),
    path("list/authors/", views.AuthorList.as_view(), name="authors_list"),
    path("list/authors/paginated/", views.AuthorList.as_view(paginate_by=30)),
    path(
        "list/authors/paginated/<int:page>/", views.AuthorList.as_view(paginate_by=30)
    ),
    path(
        "list/authors/paginated-orphaned/",
        views.AuthorList.as_view(paginate_by=30, paginate_orphans=2),
    ),
    path("list/authors/notempty/", views.AuthorList.as_view(allow_empty=False)),
    path(
        "list/authors/notempty/paginated/",
        views.AuthorList.as_view(allow_empty=False, paginate_by=2),
    ),
    path(
        "list/authors/template_name/",
        views.AuthorList.as_view(template_name="test_generic_views/list.html"),
    ),
    path(
        "list/authors/template_name_suffix/",
        views.AuthorList.as_view(template_name_suffix="_objects"),
    ),
    path(
        "list/authors/context_object_name/",
        views.AuthorList.as_view(context_object_name="author_list"),
    ),
    path(
        "list/authors/dupe_context_object_name/",
        views.AuthorList.as_view(context_object_name="object_list"),
    ),
    path("list/authors/invalid/", views.AuthorList.as_view(queryset=None)),
    path(
        "list/authors/get_queryset/",
        views.AuthorListGetQuerysetReturnsNone.as_view(),
    ),
    path(
        "list/authors/paginated/custom_class/",
        views.AuthorList.as_view(paginate_by=5, paginator_class=views.CustomPaginator),
    ),
    path(
        "list/authors/paginated/custom_page_kwarg/",
        views.AuthorList.as_view(paginate_by=30, page_kwarg="pagina"),
    ),
    path(
        "list/authors/paginated/custom_constructor/",
        views.AuthorListCustomPaginator.as_view(),
    ),
    path("list/books/sorted/", views.BookList.as_view(ordering="name")),
    path(
        "list/books/sortedbypagesandnamedec/",
        views.BookList.as_view(ordering=("pages", "-name")),
    ),
    # Useful for testing redirects
    path("accounts/login/", auth_views.LoginView.as_view()),
    # path("BaseDateListViewTest/", dates.BaseDateListView.as_view()),
]
