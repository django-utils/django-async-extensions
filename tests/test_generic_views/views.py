from django_async_extensions.aviews import generic


class CustomTemplateView(generic.AsyncTemplateView):
    template_name = "generic_views/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"key": "value"})
        return context
