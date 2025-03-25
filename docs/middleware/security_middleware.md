# AsyncSecurityMiddleware

it works exactly like django's [SecurityMiddleware](https://docs.djangoproject.com/en/5.1/ref/middleware/#module-django.middleware.security)
except that it's fully async

### Usage:
remove django's `django.middleware.security.SecurityMiddleware` from the `MIDDLEWARE` setting and add
`django_async_extensions.middleware.security.AsyncSecurityMiddleware` in it's place.

**note**: this middleware like other middlewares provided in this package can work alongside sync middlewares, and can handle sync views.
