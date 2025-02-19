Hi!
thanks for considering contribution to this project.

this is a community project and maintained by people, so we appreciate any help.

if you want to add a new future, please open an [issue](https://github.com/amirreza8002/django-async-extensions/issues) first.

Requirements:
1. python >= 3.10
2. poetry >= 2.0


contribution steps:

1. fork the project from the [repository](https://github.com/amirreza8002/django-async-extensions)
2. clone the forked repo (you can find it in your own repositories)
3. go to the cloned project's directory (probably `cd django-async-extensions` will do it for you)

4. install dependencies:
    this project uses [poetry](https://python-poetry.org/) to manage dependencies, so you want to install poetry first if you haven't.
    
    in the project directory (where `pyproject.toml` exists) run `poetry sync --with dev` to get the packages.
    if you are writing documentations, run `poetry sync --with doc`
    if you want to use ipython so you can `await` in the shell, run `poetry sync --with ipython`
    if you need al of these, run `poetry sync --all-groups`

5. activate the virtual env:
    to activate poetry follow one of the ways explained [here](https://python-poetry.org/docs/managing-environments/#activating-the-environment) depending on your OS and shell.

6. write the code/document you want

7. testing:
    tests are written using pytest.
    to run the test suits simply run `python tests/runtest.py`
    currently these flags are avilable:
    * --quite
    * -v={0,2,3}
    * --failfast
    * --keepdb

8. documentation:
    docs are written using [mkdocs](https://www.mkdocs.org/)
    you can run `mkdocs serve` so you can see the changes you make as you develop.

9. git:
    we expect a clean git history, you can use the many sources available online to see how you can keep a clean git history.

10. sending the codes:
    first push your changes to your forked repo (using `git push origin main` or the like)
    then go to the repo and click on the button saying `Contribute`
    then open a pull request, we'll check the code and either accept or add notes to it.
