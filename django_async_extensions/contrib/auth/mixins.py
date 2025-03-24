from urllib.parse import urlparse

from asgiref.sync import sync_to_async
from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.shortcuts import resolve_url


class AsyncAccessMixin(AccessMixin):
    async def handle_no_permission(self):
        user = await self.request.auser()
        if self.raise_exception or user.is_authenticated:
            raise PermissionDenied(self.get_permission_denied_message())

        path = self.request.build_absolute_uri()
        resolved_login_url = resolve_url(self.get_login_url())
        # If the login url is the same scheme and net location then use the
        # path as the "next" url.
        login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
        current_scheme, current_netloc = urlparse(path)[:2]
        if (not login_scheme or login_scheme == current_scheme) and (
            not login_netloc or login_netloc == current_netloc
        ):
            path = self.request.get_full_path()
        return redirect_to_login(
            path,
            resolved_login_url,
            self.get_redirect_field_name(),
        )


class AsyncLoginRequiredMixin(AsyncAccessMixin):
    """Verify that the current user is authenticated."""

    async def dispatch(self, request, *args, **kwargs):
        user = await request.auser()
        if not user.is_authenticated:
            return await self.handle_no_permission()
        return await super().dispatch(request, *args, **kwargs)


class AsyncPermissionRequiredMixin(AsyncAccessMixin):
    """Verify that the current user has all specified permissions."""

    permission_required = None

    def get_permission_required(self):
        """
        Override this method to override the permission_required attribute.
        Must return an iterable.
        """
        if self.permission_required is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} is missing the "
                f"permission_required attribute. Define "
                f"{self.__class__.__name__}.permission_required, or override "
                f"{self.__class__.__name__}.get_permission_required()."
            )
        if isinstance(self.permission_required, str):
            perms = (self.permission_required,)
        else:
            perms = self.permission_required
        return perms

    async def has_permission(self):
        perms = self.get_permission_required()
        user = await self.request.auser()
        return await sync_to_async(user.has_perms)(perms)

    async def dispatch(self, request, *args, **kwargs):
        if not await self.has_permission():
            return await self.handle_no_permission()
        return await super().dispatch(request, *args, **kwargs)


class AsyncUserPassesTestMixin(AsyncAccessMixin):
    """
    Deny a request with a permission error if the test_func() method returns
    False.
    """

    async def test_func(self):
        raise NotImplementedError(
            "{} is missing the implementation of the test_func() method.".format(
                self.__class__.__name__
            )
        )

    def get_test_func(self):
        """
        Override this method to use a different test_func method.
        """
        return self.test_func

    async def dispatch(self, request, *args, **kwargs):
        user_test_result = await self.get_test_func()()
        if not user_test_result:
            return await self.handle_no_permission()
        return await super().dispatch(request, *args, **kwargs)
