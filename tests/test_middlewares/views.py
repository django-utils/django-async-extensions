from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.common import no_append_slash

from django_async_extensions.aviews.generic.base import AsyncView


async def empty_view(request, *args, **kwargs):
    return HttpResponse()


@no_append_slash
async def sensitive_fbv(request, *args, **kwargs):
    return HttpResponse()


@method_decorator(no_append_slash, name="dispatch")
class SensitiveCBV(AsyncView):
    async def get(self, *args, **kwargs):
        return HttpResponse()
