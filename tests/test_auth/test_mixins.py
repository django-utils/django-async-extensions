from functools import partial

import pytest

from django.contrib.auth import models
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import AsyncClient, AsyncRequestFactory

from django_async_extensions.contrib.auth.mixins import (
    AsyncLoginRequiredMixin,
    AsyncPermissionRequiredMixin,
    AsyncUserPassesTestMixin,
)
from django_async_extensions.views.generic.base import AsyncView

aclient = AsyncClient()


async def auser(request, user):
    request._acached_user = user
    return request._acached_user


class AlwaysTrueMixin(AsyncUserPassesTestMixin):
    async def test_func(self):
        return True


class AlwaysFalseMixin(AsyncUserPassesTestMixin):
    async def test_func(self):
        return False


class EmptyResponseView(AsyncView):
    async def get(self, request, *args, **kwargs):
        return HttpResponse()


class AlwaysTrueView(AlwaysTrueMixin, EmptyResponseView):
    pass


class AlwaysFalseView(AlwaysFalseMixin, EmptyResponseView):
    pass


class StackedMixinsView1(
    AsyncLoginRequiredMixin, AsyncPermissionRequiredMixin, EmptyResponseView
):
    permission_required = ["test_auth.add_customuser", "test_auth.change_customuser"]
    raise_exception = True


class StackedMixinsView2(
    AsyncPermissionRequiredMixin, AsyncLoginRequiredMixin, EmptyResponseView
):
    permission_required = ["test_auth.add_customuser", "test_auth.change_customuser"]
    raise_exception = True


@pytest.mark.django_db(transaction=True)
class TestAccessMixin:
    factory = AsyncRequestFactory()

    async def test_stacked_mixins_success(self):
        user = await models.User.objects.acreate(
            username="joe", password="qwerty"  # noqa: S106
        )
        perms = models.Permission.objects.filter(
            codename__in=("add_customuser", "change_customuser")
        )
        await user.user_permissions.aadd(*[perm async for perm in perms])
        request = self.factory.get("/rand")
        request.auser = partial(auser, request, user)

        view = StackedMixinsView1.as_view()
        response = await view(request)
        assert response.status_code == 200

        view = StackedMixinsView2.as_view()
        response = await view(request)
        assert response.status_code == 200

    async def test_stacked_mixins_missing_permission(self):
        user = await models.User.objects.acreate(
            username="joe", password="qwerty"  # noqa: S106
        )
        perms = models.Permission.objects.filter(codename__in=("add_customuser",))
        await user.user_permissions.aadd(*[perm async for perm in perms])
        request = self.factory.get("/rand")
        request.auser = partial(auser, request, user)

        view = StackedMixinsView1.as_view()
        with pytest.raises(PermissionDenied):
            await view(request)

        view = StackedMixinsView2.as_view()
        with pytest.raises(PermissionDenied):
            await view(request)

    async def test_access_mixin_permission_denied_response(self):
        user = await models.User.objects.acreate(
            username="joe", password="qwerty"  # noqa: S106
        )
        # Authenticated users receive PermissionDenied.
        request = self.factory.get("/rand")
        request.auser = partial(auser, request, user)
        view = AlwaysFalseView.as_view()
        with pytest.raises(PermissionDenied):
            await view(request)
        # Anonymous users are redirected to the login page.
        request.auser = partial(auser, request, AnonymousUser())
        response = await view(request)
        assert response.status_code == 302
        assert response.url == "/accounts/login/?next=/rand"

    async def test_access_mixin_permission_denied_remote_login_url(self):
        class AView(AlwaysFalseView):
            login_url = "https://www.remote.example.com/login"

        view = AView.as_view()
        request = self.factory.get("/rand")
        request.auser = partial(auser, request, AnonymousUser())
        response = await view(request)
        assert response.status_code == 302
        assert (
            response.url
            == "https://www.remote.example.com/login?next=http%3A//testserver/rand"
        )

    async def test_stacked_mixins_not_logged_in(self, mocker):
        mocker.patch.object(models.User, "is_authenticated", False)
        user = await models.User.objects.acreate(
            username="joe", password="qwerty"  # noqa: S106
        )
        perms = models.Permission.objects.filter(
            codename__in=("add_customuser", "change_customuser")
        )
        await user.user_permissions.aadd(*[perm async for perm in perms])
        request = self.factory.get("/rand")
        request.auser = partial(auser, request, user)

        view = StackedMixinsView1.as_view()
        with pytest.raises(PermissionDenied):
            await view(request)

        view = StackedMixinsView2.as_view()
        with pytest.raises(PermissionDenied):
            await view(request)


class TestUserPassesTest:
    factory = AsyncRequestFactory()

    async def _test_redirect(self, view=None, url="/accounts/login/?next=/rand"):
        if not view:
            view = AlwaysFalseView.as_view()
        request = self.factory.get("/rand")
        request.auser = partial(auser, request, AnonymousUser())
        response = await view(request)
        assert response.status_code == 302
        assert response.url == url

    async def test_default(self):
        await self._test_redirect()

    async def test_custom_redirect_url(self):
        class AView(AlwaysFalseView):
            login_url = "/login/"

        await self._test_redirect(AView.as_view(), "/login/?next=/rand")

    async def test_custom_redirect_parameter(self):
        class AView(AlwaysFalseView):
            redirect_field_name = "goto"

        await self._test_redirect(AView.as_view(), "/accounts/login/?goto=/rand")

    async def test_no_redirect_parameter(self):
        class AView(AlwaysFalseView):
            redirect_field_name = None

        await self._test_redirect(AView.as_view(), "/accounts/login/")

    async def test_raise_exception(self):
        class AView(AlwaysFalseView):
            raise_exception = True

        request = self.factory.get("/rand")
        request.auser = partial(auser, request, AnonymousUser())
        with pytest.raises(PermissionDenied):
            await AView.as_view()(request)

    async def test_raise_exception_custom_message(self):
        msg = "You don't have access here"

        class AView(AlwaysFalseView):
            raise_exception = True
            permission_denied_message = msg

        request = self.factory.get("/rand")
        request.auser = partial(auser, request, AnonymousUser())
        view = AView.as_view()
        with pytest.raises(PermissionDenied, match=msg):
            await view(request)

    async def test_raise_exception_custom_message_function(self):
        msg = "You don't have access here"

        class AView(AlwaysFalseView):
            raise_exception = True

            def get_permission_denied_message(self):
                return msg

        request = self.factory.get("/rand")
        request.auser = partial(auser, request, AnonymousUser())
        view = AView.as_view()
        with pytest.raises(PermissionDenied, match=msg):
            await view(request)

    async def test_user_passes(self):
        view = AlwaysTrueView.as_view()
        request = self.factory.get("/rand")
        request.auser = partial(auser, request, AnonymousUser())
        response = await view(request)
        assert response.status_code == 200


@pytest.mark.django_db(transaction=True)
class TestLoginRequiredMixin:
    factory = AsyncRequestFactory()

    @pytest.fixture(autouse=True)
    async def setup(self):
        self.user = await models.User.objects.acreate(
            username="joe", password="qwerty"  # noqa: S106
        )

    async def test_login_required(self):
        """
        login_required works on a simple view wrapped in a login_required
        decorator.
        """

        class AView(AsyncLoginRequiredMixin, EmptyResponseView):
            pass

        view = AView.as_view()

        request = self.factory.get("/rand")
        request.auser = partial(auser, request, AnonymousUser())
        response = await view(request)
        assert response.status_code == 302
        assert "/accounts/login/?next=/rand" == response.url
        await aclient.alogin(username=self.user.username, password=self.user.password)
        request = self.factory.get("/rand")
        request.auser = partial(auser, request, self.user)
        response = await view(request)
        assert response.status_code == 200


@pytest.mark.django_db(transaction=True)
class TestPermissionsRequiredMixin:
    factory = AsyncRequestFactory()

    @pytest.fixture(autouse=True)
    async def setup(self):
        self.user = await models.User.objects.acreate(
            username="joe", password="qwerty"  # noqa: S106
        )
        perms = models.Permission.objects.filter(
            codename__in=("add_customuser", "change_customuser")
        )
        await self.user.user_permissions.aadd(*[perm async for perm in perms])

    async def test_many_permissions_pass(self):
        class AView(AsyncPermissionRequiredMixin, EmptyResponseView):
            permission_required = [
                "test_auth.add_customuser",
                "test_auth.change_customuser",
            ]

        request = self.factory.get("/rand")
        request.auser = partial(auser, request, self.user)
        resp = await AView.as_view()(request)
        assert resp.status_code == 200

    async def test_single_permission_pass(self):
        class AView(AsyncPermissionRequiredMixin, EmptyResponseView):
            permission_required = "test_auth.add_customuser"

        request = self.factory.get("/rand")
        request.auser = partial(auser, request, self.user)
        resp = await AView.as_view()(request)
        assert resp.status_code == 200

    async def test_permissioned_denied_redirect(self):
        class AView(AsyncPermissionRequiredMixin, EmptyResponseView):
            permission_required = [
                "test_auth.add_customuser",
                "test_auth.change_customuser",
                "nonexistent-permission",
            ]

        # Authenticated users receive PermissionDenied.
        request = self.factory.get("/rand")
        request.auser = partial(auser, request, self.user)
        with pytest.raises(PermissionDenied):
            await AView.as_view()(request)
        # Anonymous users are redirected to the login page.
        request.auser = partial(auser, request, AnonymousUser())
        resp = await AView.as_view()(request)
        assert resp.status_code == 302

    async def test_permissioned_denied_exception_raised(self):
        class AView(AsyncPermissionRequiredMixin, EmptyResponseView):
            permission_required = [
                "test_auth.add_customuser",
                "test_auth.change_customuser",
                "nonexistent-permission",
            ]
            raise_exception = True

        request = self.factory.get("/rand")
        request.auser = partial(auser, request, self.user)
        with pytest.raises(PermissionDenied):
            await AView.as_view()(request)
