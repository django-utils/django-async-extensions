import argparse
import os
import pathlib
import socket
import sys
import tempfile

import django
from django.apps import apps
from django.conf import settings
from django.test.utils import NullTimeKeeper, TimeKeeper, get_runner

RUNTESTS_DIR = pathlib.Path(__file__).parent.absolute()
TEMPLATE_DIR = RUNTESTS_DIR / "templates"
TMPDIR = tempfile.mkdtemp(prefix="django_")

ALWAYS_INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sites",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin.apps.SimpleAdminConfig",
    "django.contrib.staticfiles",
]

ALWAYS_MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]


def get_test_modules():
    discovery_dirs = [""]
    for dirname in discovery_dirs:
        dirpath = os.path.join(RUNTESTS_DIR, dirname)
        with os.scandir(dirpath) as entries:
            for f in entries:
                if (
                    "." in f.name
                    or f.is_file()
                    or not os.path.exists(os.path.join(f.path, "__init__.py"))
                ):
                    continue
                test_module = f.name
                if dirname:
                    test_module = dirname + "." + test_module
                yield "tests/" + test_module


def get_label_module(label):
    path = pathlib.Path(label)
    if len(path.parts) == 1:
        return label.split(".")[0]

    if not path.exists():
        raise RuntimeError(f"Test label path {label} does not exist")
    path = path.resolve()
    rel_path = path.relative_to(RUNTESTS_DIR)
    return rel_path.parts[0]


def get_filtered_tests_modules(start_at, start_after, test_labels=None):
    if test_labels is None:
        test_labels = []

    label_modules = set()
    for label in test_labels:
        test_module = get_label_module(label)
        label_modules.add(test_module)

    def _module_match_label(module_name, label):
        return module_name == label or module_name.startswith(label + ".")

    start_label = start_at or start_after
    for test_module in get_test_modules():
        if start_label:
            if not _module_match_label(test_module, start_label):
                continue
            start_label = ""
            if not start_at:
                assert start_after
                continue

        if not test_labels or any(
            _module_match_label(test_module, label_module)
            for label_module in label_modules
        ):
            yield test_module


def setup_collect_tests(start_at, start_after, test_labels=None):
    state = {
        "INSTALLED_APPS": settings.INSTALLED_APPS,
        "MIDDLEWARE": settings.MIDDLEWARE,
        "ROOT_URLCONF": getattr(settings, "ROOT_URLCONF", ""),
    }

    settings.INSTALLED_APPS = ALWAYS_INSTALLED_APPS
    settings.LANGUAGE_CODE = "en"
    settings.SITE_ID = 1
    settings.MIDDLEWARE = ALWAYS_MIDDLEWARE
    settings.MIGRATION_MODULES = {
        # This lets us skip creating migrations for the test models as many of
        # them depend on one of the following contrib applications.
        "auth": None,
        "contenttypes": None,
        "sessions": None,
    }
    settings.STATIC_URL = "static/"
    settings.STATIC_ROOT = os.path.join(TMPDIR, "static")
    settings.TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [TEMPLATE_DIR],
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ],
            },
        }
    ]

    django.setup()

    test_modules = list(get_filtered_tests_modules(start_at, start_after, test_labels))
    return test_modules, state


def teardown_collect_tests(state):
    for key, value in state.items():
        setattr(settings, key, value)


def get_installed():
    return [app_config.name for app_config in apps.get_app_configs()]


def setup_run_tests(verbosity, start_at, start_after, test_labels=None):
    test_modules, state = setup_collect_tests(start_at, start_after, test_labels)
    apps.set_installed_apps(settings.INSTALLED_APPS)
    # Set an environment variable that other code may consult to see if
    # Django's own test suite is running.
    os.environ["RUNNING_DJANGOS_TEST_SUITE"] = "true"

    test_labels = test_labels or test_modules
    return test_labels, state


def teardown_run_tests(state):
    teardown_collect_tests(state)
    # Discard the multiprocessing.util finalizer that tries to remove a
    # temporary directory that's already removed by this script's
    # atexit.register(shutil.rmtree, TMPDIR) handler. Prevents
    # FileNotFoundError at the end of a test run (#27890).
    from multiprocessing.util import _finalizer_registry

    _finalizer_registry.pop((-100, 0), None)
    del os.environ["RUNNING_DJANGOS_TEST_SUITE"]


def async_tests(
    verbosity,
    interactive,
    failfast,
    keepdb,
    reverse,
    test_labels,
    debug_sql,
    parallel,
    tags,
    exclude_tags,
    test_name_patterns,
    start_at,
    start_after,
    pdb,
    buffer,
    timing,
    shuffle,
    durations=None,
):
    if verbosity >= 1:
        msg = "testing django-async-extensions"
        print(msg)  # noqa T201

    process_setup_args = (verbosity, start_at, start_after, test_labels)
    test_labels, state = setup_run_tests(*process_setup_args)

    if not hasattr(settings, "TEST_RUNNER"):
        settings.TEST_RUNNER = "tests.runner.PytestTestRunner"

    TestRunner = get_runner(settings)
    test_runner = TestRunner(
        verbosity=verbosity,
        interactive=interactive,
        failfast=failfast,
        keepdb=keepdb,
        reverse=reverse,
        debug_sql=debug_sql,
        parallel=parallel,
        tags=tags,
        exclude_tags=exclude_tags,
        test_name_patterns=test_name_patterns,
        pdb=pdb,
        buffer=buffer,
        timing=timing,
        shuffle=shuffle,
        durations=durations,
    )
    failures = test_runner.run_tests(test_labels)
    teardown_run_tests(state)
    return failures


def collect_test_modules(start_at, start_after):
    test_modules, state = setup_collect_tests(start_at, start_after)
    teardown_collect_tests(state)
    return test_modules


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Django test suite.")
    parser.add_argument(
        "modules",
        nargs="*",
        metavar="module",
        help='Optional path(s) to test modules; e.g. "i18n" or '
        '"i18n.tests.TranslationTests.test_lazy_objects".',
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        default=1,
        type=int,
        choices=[0, 1, 2, 3],
        help="Verbosity level; 0=minimal output, 1=normal output, 2=all output",
    )
    parser.add_argument(
        "--noinput",
        action="store_false",
        dest="interactive",
        help="Tells Django to NOT prompt the user for input of any kind.",
    )
    parser.add_argument(
        "--failfast",
        action="store_true",
        help="Tells Django to stop running the test suite after first failed test.",
    )
    parser.add_argument(
        "--keepdb",
        action="store_true",
        help="Tells Django to preserve the test database between runs.",
    )
    parser.add_argument(
        "--settings",
        help='Python path to settings module, e.g. "myproject.settings". If '
        "this isn't provided, either the DJANGO_SETTINGS_MODULE "
        'environment variable or "test_sqlite" will be used.',
    )
    parser.add_argument(
        "--shuffle",
        nargs="?",
        default=False,
        type=int,
        metavar="SEED",
        help=(
            "Shuffle the order of test cases to help check that tests are "
            "properly isolated."
        ),
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Sort test suites and test cases in opposite order to debug "
        "test side effects not apparent with normal execution lineup.",
    )
    parser.add_argument(
        "--screenshots",
        action="store_true",
        help="Take screenshots during selenium tests to capture the user interface.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run selenium tests in headless mode, if the browser supports the option.",
    )
    parser.add_argument(
        "--external-host",
        default=socket.gethostname(),
        help=(
            "The external host that can be reached by the selenium hub instance when "
            "running Selenium tests via Selenium Hub."
        ),
    )
    parser.add_argument(
        "--debug-sql",
        action="store_true",
        help="Turn on the SQL query logger within tests.",
    )
    parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        help="Run only tests with the specified tags. Can be used multiple times.",
    )
    parser.add_argument(
        "--exclude-tag",
        dest="exclude_tags",
        action="append",
        help="Do not run tests with the specified tag. Can be used multiple times.",
    )
    parser.add_argument(
        "--start-after",
        dest="start_after",
        help="Run tests starting after the specified top-level module.",
    )
    parser.add_argument(
        "--start-at",
        dest="start_at",
        help="Run tests starting at the specified top-level module.",
    )
    parser.add_argument(
        "--pdb", action="store_true", help="Runs the PDB debugger on error or failure."
    )
    parser.add_argument(
        "-b",
        "--buffer",
        action="store_true",
        help="Discard output of passing tests.",
    )
    parser.add_argument(
        "--timing",
        action="store_true",
        help="Output timings, including database set up and total run time.",
    )
    parser.add_argument(
        "-k",
        dest="test_name_patterns",
        action="append",
        help=(
            "Only run test methods and classes matching test name pattern. "
            "Same as unittest -k option. Can be used multiple times."
        ),
    )
    parser.add_argument(
        "--durations",
        dest="durations",
        type=int,
        default=None,
        metavar="N",
        help="Show the N slowest test cases (N=0 for all).",
    )

    options = parser.parse_args()

    # Allow including a trailing slash on app_labels for tab completion convenience
    options.modules = [os.path.normpath(labels) for labels in options.modules]

    mutually_exclusive_options = [
        options.start_at,
        options.start_after,
        options.modules,
    ]
    enabled_module_options = [
        bool(option) for option in mutually_exclusive_options
    ].count(True)
    if enabled_module_options > 1:
        print(  # noqa T201
            "Aborting: --start-at, --start-after, and test labels are mutually "
            "exclusive."
        )
        sys.exit(1)
    for opt_name in ["start_at", "start_after"]:
        opt_val = getattr(options, opt_name)
        if opt_val:
            if "." in opt_val:
                print(  # noqa T201
                    "Aborting: --%s must be a top-level module."
                    % opt_name.replace("_", "-")
                )
                sys.exit(1)
            setattr(options, opt_name, os.path.normpath(opt_val))
    if options.settings:
        os.environ["DJANGO_SETTINGS_MODULE"] = options.settings
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
        options.settings = os.environ["DJANGO_SETTINGS_MODULE"]

    time_keeper = TimeKeeper() if options.timing else NullTimeKeeper()
    with time_keeper.timed("Total run"):
        failures = async_tests(
            options.verbosity,
            options.interactive,
            options.failfast,
            options.keepdb,
            options.reverse,
            options.modules,
            options.debug_sql,
            options.tags,
            options.exclude_tags,
            options.test_name_patterns,
            options.start_at,
            options.start_after,
            options.pdb,
            options.buffer,
            options.timing,
            options.shuffle,
            getattr(options, "durations", None),
        )
    time_keeper.print_results()
    if failures:
        sys.exit(1)
