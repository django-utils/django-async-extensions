from runtests import setup_run_tests, teardown_run_tests

state = None


def pytest_sessionstart(session):
    global state
    process_setup_args = (0, None, False, None)
    test_labels, state = setup_run_tests(*process_setup_args)


def pytest_sessionfinish(session, exitstatus):
    teardown_run_tests(state)
