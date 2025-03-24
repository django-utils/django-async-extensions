from asgiref.sync import sync_to_async

from django.utils.safestring import mark_safe


class AsyncRenderableMixin:
    async def arender(self, template_name=None, context=None, renderer=None):
        renderer = renderer or self.renderer
        template = template_name or self.template_name
        context = context or self.get_context()
        return mark_safe(  # noqa:S308
            await sync_to_async(renderer.render)(template, context)
        )


class AsyncRenderableFormMixin(AsyncRenderableMixin):
    async def aas_p(self):
        """Render as <p> elements."""
        return await self.arender(self.template_name_p)

    async def aas_table(self):
        """Render as <tr> elements excluding the surrounding <table> tag."""
        return await self.arender(self.template_name_table)

    async def aas_ul(self):
        """Render as <li> elements excluding the surrounding <ul> tag."""
        return await self.arender(self.template_name_ul)

    async def aas_div(self):
        """Render as <div> elements."""
        return await self.arender(self.template_name_div)
