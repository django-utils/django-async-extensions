from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse, StreamingHttpResponse
from django.urls import path
from django.utils.translation import gettext_lazy as _


from . import views


async def stream_http_generator():
    yield _("Yes")
    yield "/"
    yield _("No")


urlpatterns = [
    path("middleware_exceptions/view/", views.normal_view),
    path("middleware_exceptions/error/", views.server_error),
    path("middleware_exceptions/permission_denied/", views.permission_denied),
    path("middleware_exceptions/exception_in_render/", views.exception_in_render),
    path("middleware_exceptions/template_response/", views.template_response),
    # Async views.
    path(
        "middleware_exceptions/async_exception_in_render/",
        views.async_exception_in_render,
    ),
]

urlpatterns += i18n_patterns(
    path("simple/", lambda r: HttpResponse()),
    path("streaming/", lambda r: StreamingHttpResponse(stream_http_generator())),
)
