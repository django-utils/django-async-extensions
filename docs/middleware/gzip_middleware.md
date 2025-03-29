# AsyncGZipMiddleware

it works exactly like django's [GZipMiddleware](https://docs.djangoproject.com/en/5.1/ref/middleware/#module-django.middleware.gzip)
except that it's fully async

------------------------
**important:**
Security researchers revealed that when compression techniques (including GZipMiddleware) are used on a website, the site may become exposed to a number of possible attacks.

To mitigate attacks, Django implements a technique called Heal The Breach (HTB). It adds up to 100 bytes (see [max_random_bytes](https://docs.djangoproject.com/en/5.1/ref/middleware/#django.middleware.gzip.GZipMiddleware.max_random_bytes)) of random bytes to each response to make the attacks less effective.

For more details, see the [BREACH paper (PDF)](https://www.breachattack.com/resources/BREACH%20-%20SSL,%20gone%20in%2030%20seconds.pdf), [breachattack.com](https://www.breachattack.com/), and the [Heal The Breach (HTB) paper](https://ieeexplore.ieee.org/document/9754554).

-------------------------

### Usage:
remove django's `django.middleware.gzip.GZipMiddleware` from the `MIDDLEWARE` setting (if it's in there) and add
`django_async_extensions.middleware.gzip.AsyncGZipMiddleware` in it's place.

**note**: this middleware like other middlewares provided in this package can work alongside sync middlewares, and can handle sync views.
