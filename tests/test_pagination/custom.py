from django_async_extensions.acore.paginator import AsyncPaginator, AsyncPage


class AsyncValidAdjacentNumsPage(AsyncPage):
    async def anext_page_number(self):
        if not await self.ahas_next():
            return None
        return await super().anext_page_number()

    async def aprevious_page_number(self):
        if not await self.ahas_previous():
            return None
        return await super().aprevious_page_number()


class AsyncValidAdjacentNumsPaginator(AsyncPaginator):
    def _get_page(self, *args, **kwargs):
        return AsyncValidAdjacentNumsPage(*args, **kwargs)
