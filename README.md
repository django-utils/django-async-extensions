# Async stuff for django

I did not do this because it was easy,
I did it because I thought it would be easy.


## What is this?

django-async-extensions is a package that contains various async tools to be used in a django project,


this might be something django doesn't have yet,
something django can't add (due to maintenance problems or backwards compatibility), 
or something else.


## What does it do?

these tools are provided for now:

1. async class based views (AsyncView).
2. async generic class based views.
3. async paginator
4. async auth mixins 

more to come...

## Where are the docs?

you can find our [documentations here](https://django-async-extensions.readthedocs.io/en/latest/)

## How to install this?

```shell
pip install django-async-extensions
```

no need to add this to `INSTALLED_APPS`.

## Can I use this?
the package should work with the stable versions of django and python.
there shouldn't be any problems using it with other versions, but it is not tested.

## is this for everyone?
this package is developed by the community for the community and is available for everyone under MIT licence.

## Q&A

1. does this package solve all the async problems django has?

no, we provide some tools to help with some stuff,
but some stuff need to be solved in django itself.

2. does this make async programming easier?

no, it makes async programming with django easier,
you still need to know how to do async programming.

3. is this production ready?

the codebase is well tested, but the package is new and not used in production, so I can't make any guarantees yet.

4. what async framework can be used for this?

django only works with `asyncio`, so this also only works with `asyncio`.
