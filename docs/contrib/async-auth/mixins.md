# Async auth mixins

django has a set of mixins that help with limiting access and enforcing authentication and permissions,
but these mixins do not work with async views.

to help with that an async version of the mixins are included in the `acontrib.auth.mixins` module.

**note**: these mixins only work with `AsyncView` or classes that inherit from it, or implement the same logic.

## AsyncAccessMixin
[django.contrib.auth.mixins.AccessMixin](https://docs.djangoproject.com/en/5.1/topics/auth/default/#django.contrib.auth.mixins.AccessMixin) handles the behaviour of a view when access should be denied,
the `AsyncAccessMixin` class works similarly to django's version, except that the `handle_no_permission()` method is async.

## AsyncLoginRequiredMixin
works similar to [LoginRequiredMixin](https://docs.djangoproject.com/en/5.1/topics/auth/default/#the-loginrequiredmixin-mixin) but inherits from `AsyncAccessMixin`,
also the `dispatch()` method is async.

```python
from django_async_extensions.acontrib.auth.mixins import AsyncLoginRequiredMixin


class MyView(AsyncLoginRequiredMixin, AsyncView):
    login_url = "/login/"
    redirect_field_name = "redirect_to"
```

## AsyncPermissionRequiredMixin
works similar to [PermissionRequiredMixin](https://docs.djangoproject.com/en/5.1/topics/auth/default/#the-permissionrequiredmixin-mixin)
with a few differences:

1. `AsyncPermissionRequiredMixin` inherits from `AsyncAccessMixin`.
2. `has_permission()` method is async.
3. `dispatch()` method is async.

## AsyncUserPassesTestMixin
works similar to [UserPassesTestMixin](https://docs.djangoproject.com/en/5.1/topics/auth/default/#django.contrib.auth.mixins.UserPassesTestMixin)
with a few differences:

1. `AsyncUserPassesTestMixin` inherits from `AsyncAccessMixin`.
2. `test_func()` method is async.
3. `dispatch()` method is async.
