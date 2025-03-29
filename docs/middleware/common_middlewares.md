# Common Middlewares

## AsyncCommonMiddleware
it works exactly like django's [CommonMiddleware](https://docs.djangoproject.com/en/5.1/ref/middleware/#django.middleware.common.CommonMiddleware)
except that it's fully async

### Usage:
remove django's `django.middleware.common.CommonMiddleware` from the `MIDDLEWARE` setting and add
`django_async_extensions.middleware.common.AsyncCommonMiddleware` in it's place.



## AsyncBrokenLinkEmailsMiddleware
it works exactly like django's [BrokenLinkEmailsMiddleware](https://docs.djangoproject.com/en/5.1/ref/middleware/#django.middleware.common.BrokenLinkEmailsMiddleware)
except that it's fully async

### Usage:
remove django's `django.middleware.common.LinkEmailsMiddleware` from the `MIDDLEWARE` setting if it's in there and add
`django_async_extensions.middleware.common.AsyncBrokenLinkEmailsMiddleware` in it's place.


**note**: these two middlewares like other middlewares provided in this package can work alongside sync middlewares, and can handle sync views.
