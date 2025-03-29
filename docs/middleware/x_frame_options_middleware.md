# AsyncXFrameOptionsMiddleware

it works exactly like django's [XFrameOptionsMiddleware](https://docs.djangoproject.com/en/5.1/ref/middleware/#x-frame-options-middleware)
except that it's fully async

### Usage:
remove django's `django.middleware.clickjacking.XFrameOptionsMiddleware` from the `MIDDLEWARE` setting and add
`django_async_extensions.middleware.clickjacking.AsyncXFrameOptionsMiddleware` in it's place.

**note**: this middleware like other middlewares provided in this package can work alongside sync middlewares, and can handle sync views.
