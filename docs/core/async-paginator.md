## AsyncPaginator

the `AsyncPaginator` class is an async version of django's [Paginator](https://docs.djangoproject.com/en/5.1/ref/paginator/#django.core.paginator.Paginator).

although `AsyncPaginator` inherits from django's `Paginator`, but this is only for code reuse and easier migration from sync to async, and you should not call the sync methods from an async environment.

the paginator can take a queryset or a list, but they have slightly different behaviours,
if you pass in a queryset to the paginator, the queryset is preserved until it has to be evaluated, so until it is evaluated it needs to be treated as a queryset,
and using querysets in an async environment is different from using querysets in sync environments.

### Examples

**note**: in normal django shell you can not `await`, to use `await` you need a shell tht supports that, such as [ipython](https://ipython.org/)

#### Example of list pagination

```pycon
In [1]: from django_async_extensions.core.paginator import AsyncPaginator

In [2]: objects = ["john", "paul", "george", "ringo"]

In [3]: p = AsyncPaginator(objects, 2)

In [4]: await p.acount()
Out[4]: 4

In [5]: await p.anum_pages()
Out[5]: 2

In [6]: type(await p.apage_range())
Out[6]: range

In [7]: await p.apage_range()
Out[7]: range(1, 3)

In [8]: page1 = await p.apage(1)

In [9]: page1
Out[9]: <Async Page 1>

In [10]: page1.object_list
Out[10]: ['john', 'paul']

In [11]: page2 = await p.apage(2)

In [12]: page2.object_list
Out[12]: ['george', 'ringo']

In [13]: await page2.ahas_next()
Out[13]: False

In [14]: await page2.ahas_previous()
Out[14]: True

In [15]: await page2.ahas_other_pages()
Out[15]: True

await page2.anext_page_number()
Traceback (most recent call last):
...
EmptyPage: That page contains no results

In [17]: await page2.aprevious_page_number()
Out[17]: 1

In [18]: await page2.astart_index()
Out[18]: 3

In [19]: await page2.aend_index()
Out[19]: 4

In [20]: await p.apage(0)
Traceback (most recent call last):
...
EmptyPage: That page number is less than 1

In [21]: await p.apage(3)
Traceback (most recent call last):
...
EmptyPage: That page contains no results
```


#### Example of queryset pagination

```pycon
In [1]: from django.contrib.auth.models import User

In [2]: objs = [User(username=f"test{i}", password="testpass123") for i in range
   ...: (1, 5)]

In [3]: User.objects.bulk_create(objs)
Out[3]: [<User: test1>, <User: test2>, <User: test3>, <User: test4>]

In [4]: from django_async_extensions.core.paginator import AsyncPaginator

In [5]: users = User.objects.order_by("username")

In [6]: p = AsyncPaginator(users, 2)

In [7]: p.object_list
Out[7]: <QuerySet [<User: test1>, <User: test2>, <User: test3>, <User: test4>]>

In [8]: page1 = await p.apage(1)

In [9]: page1
Out[9]: <Async Page 1>

In [10]: page1.object_list
Out[10]: <QuerySet [<User: test1>, <User: test2>]>

In [11]: page2 = await p.apage(2)

In [12]: page2.object_list
Out[12]: <QuerySet [<User: test3>, <User: test4>]>

In [13]: await page2.ahas_next()
Out[13]: False

In [14]: await page2.alen()  # use this instead of `len()`
Out[14]: 2

In [15]: len(page2)
---------------------------------------------------------------------------
TypeError                                 Traceback (most recent call last)
Cell In[15], line 1
----> 1 len(page2)

TypeError: object of type 'AsyncPage' has no len()

In [16]: await page2.alist()  # use this instead of `list()`
Out[16]: [<User: test3>, <User: test4>]

In [17]: list(page2)
---------------------------------------------------------------------------
TypeError                                 Traceback (most recent call last)
Cell In[17], line 1
----> 1 list(page2)

TypeError: 'AsyncPage' object is not iterable

In [18]: page2.object_list
Out[19]: <QuerySet [<User: test3>, <User: test4>]>

In [20]: await page2.agetitem(1)  # use this instead of `__getitem__()`
Out[20]: <User: test4>

In [21]: page2.object_list
Out[21]: [<User: test3>, <User: test4>]  # after `agetitem()` is called, the object list gets turned into a list

In [22]: page1.object_list
Out[22]: <QuerySet [<User: test1>, <User: test2>]>

In [23]: page1[0]
---------------------------------------------------------------------------
TypeError                                 Traceback (most recent call last)
Cell In[23], line 1
----> 1 page1[0]

TypeError: 'AsyncPage' object is not subscriptable

In [24]: await page1.agetitem(slice(2))  # you can pass a slice to `agetitem()`
Out[24]: [<User: test1>, <User: test2>]

In [25]: page1.object_list
Out[25]: [<User: test1>, <User: test2>]  # turned into a list

```
