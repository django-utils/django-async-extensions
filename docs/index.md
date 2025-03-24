# django async extensions

django-async-extensions is a project that brings async support to things that django doesn't/can't support.

## Installation

check out the [installation](installation.md) guide for how to get this package.

## Features

* async generic class based views.
* async auth mixins.
* async paginator.
* async model form
* async base middleware
* more to come...

## Rational

1. async development in django is hard.
2. the django project can't bring good async support to all of its features due to maintenance costs and backwards compatibility.
3. even if django can bring a feature, since django is a big project with many different tasks to be done, it takes a long time to merge a code.
4. if we manage to take some of the burden, django itself can focus on more important tasks.
