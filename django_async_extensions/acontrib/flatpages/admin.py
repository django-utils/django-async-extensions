from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from django_async_extensions.acontrib.flatpages.forms import AsyncFlatpageForm
from django_async_extensions.acontrib.flatpages.models import AsyncFlatPage


@admin.register(AsyncFlatPage)
class FlatPageAdmin(admin.ModelAdmin):
    form = AsyncFlatpageForm
    fieldsets = (
        (None, {"fields": ("url", "title", "content", "sites")}),
        (
            _("Advanced options"),
            {
                "classes": ("collapse",),
                "fields": ("registration_required", "template_name"),
            },
        ),
    )
    list_display = ("url", "title")
    list_filter = ("sites", "registration_required")
    search_fields = ("url", "title")
