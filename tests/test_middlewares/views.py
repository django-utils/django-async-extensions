from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.template import engines
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views.decorators.common import no_append_slash

from django_async_extensions.views.generic.base import AsyncView


def normal_view(request):
    return HttpResponse("OK")


def template_response(request):
    template = engines["django"].from_string(
        "template_response OK{% for m in mw %}\n{{ m }}{% endfor %}"
    )
    return TemplateResponse(request, template, context={"mw": []})


def server_error(request):
    raise Exception("Error in view")


def permission_denied(request):
    raise PermissionDenied()


def exception_in_render(request):
    class CustomHttpResponse(HttpResponse):
        def render(self):
            raise Exception("Exception in HttpResponse.render()")

    return CustomHttpResponse("Error")


async def async_exception_in_render(request):
    class CustomHttpResponse(HttpResponse):
        async def render(self):
            raise Exception("Exception in HttpResponse.render()")

    return CustomHttpResponse("Error")


async def empty_view(request, *args, **kwargs):
    return HttpResponse()


@no_append_slash
async def sensitive_fbv(request, *args, **kwargs):
    return HttpResponse()


@method_decorator(no_append_slash, name="dispatch")
class SensitiveCBV(AsyncView):
    async def get(self, *args, **kwargs):
        return HttpResponse()
