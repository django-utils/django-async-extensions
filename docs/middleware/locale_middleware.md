# AsyncLocaleMiddleware

it works exactly like django's [LocaleMiddleware](https://docs.djangoproject.com/en/5.1/ref/middleware/#module-django.middleware.locale)
except that it's fully async
read django's [Internationalization](https://docs.djangoproject.com/en/5.1/topics/i18n/translation/) documentations for a more in depth look.

### Usage:
remove django's `django.middleware.locale.LocaleMiddleware` from the `MIDDLEWARE` setting and add
`django_async_extensions.middleware.locale.AsyncLocaleMiddleware` in it's place.

**note**: this middleware like other middlewares provided in this package can work alongside sync middlewares, and can handle sync views.
