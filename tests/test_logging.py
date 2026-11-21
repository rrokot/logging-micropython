"""Tests of logging.py, which is MicroPython's: code written for CPython's logging runs on it.

A board:       mpremote mount . run tests/test_logging.py   (the board imports ./logging.py)
The unix port: micropython tests/test_logging.py
A quick check on CPython: python -m pytest tests   (tests/conftest.py stands in for MicroPython)
"""
import io
import sys
import time

try:
    # pytest on CPython: the standard library has a logging of its own, imported already
    import importlib.util
    import os

    _spec = importlib.util.spec_from_file_location(
        "logging_micropython", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logging.py"))
    logging = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(logging)
except ImportError:
    import logging  # MicroPython: the logging.py of the mounted directory


def logger(name, fmt=None):
    """A logger of its own name that writes to a string, and the string."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    if fmt:
        handler.setFormatter(logging.Formatter(fmt))
    log = logging.getLogger(name)
    log.handlers = [handler]
    log.setLevel(logging.DEBUG)
    return log, stream


def test_a_handler_without_a_formatter_uses_the_default_format():
    log, stream = logger("plain")
    log.info("temperature %.1f", 21.5)
    assert stream.getvalue() == "INFO:plain:temperature 21.5\n"


def test_asctime_is_the_time_of_the_record():
    log, stream = logger("clock", "%(asctime)s %(message)s")
    log.warning("now")
    stamp, message = stream.getvalue().rstrip("\n").rsplit(" ", 1)
    assert message == "now"
    assert stamp != "None" and len(stamp) == len("2026-11-21 13:05:09"), stamp


def test_the_time_is_formatted_without_strftime_too():
    t = (2026, 11, 21, 13, 5, 9, 5, 325)
    assert logging.Formatter._strftime("%Y-%m-%d %H:%M:%S", t) == "2026-11-21 13:05:09"
    assert logging.Formatter._strftime("%d.%m %% %j", t) == "21.11 % %j"   # an unknown directive stays


def test_msecs_come_from_the_nanoseconds():
    saved = logging._time_ns
    logging._time_ns = lambda: 1_795_092_947_123_456_789
    try:
        record = logging.LogRecord()
        record.set("x", logging.INFO, "m")
    finally:
        logging._time_ns = saved
    assert record.msecs == 123
    assert int(record.ct) == 1_795_092_947


def test_an_exception_passed_as_exc_info_follows_its_message():
    log, stream = logger("failing", "%(levelname)s %(message)s")
    log.error("write failed", exc_info=OSError(28, "no space"))
    text = stream.getvalue()
    assert text.startswith("ERROR write failed\n"), text
    assert "OSError" in text and "no space" in text


def test_exc_info_true_tells_the_exception_being_handled():
    log, stream = logger("handled", "%(message)s")
    try:
        raise ValueError("boom")
    except ValueError:
        log.warning("parse", exc_info=True)
    if hasattr(sys, "exc_info"):
        assert "ValueError" in stream.getvalue() and "boom" in stream.getvalue()
    else:   # a MicroPython without sys.exc_info(): the message alone
        assert stream.getvalue() == "parse\n"


def test_exception_is_one_record_and_false_turns_the_traceback_off():
    log, stream = logger("once", "%(levelname)s|%(message)s")
    log.exception("reading failed", exc_info=ZeroDivisionError("division by zero"))
    assert stream.getvalue().count("ERROR|") == 1
    assert "ZeroDivisionError" in stream.getvalue()
    log, stream = logger("quiet", "%(message)s")
    log.exception("no traceback", exc_info=False)
    assert stream.getvalue() == "no traceback\n"


def test_the_module_functions_take_exc_info():
    root, stream = logger("root", "%(message)s")
    logging.error("module", exc_info=KeyError("k"))
    assert stream.getvalue().startswith("module\n") and "KeyError" in stream.getvalue()


def test_level_names_map_both_ways():
    assert logging.getLevelName(logging.ERROR) == "ERROR"
    assert logging.getLevelName("ERROR") == logging.ERROR
    assert logging.getLevelName(25) == "Level 25"


if __name__ == "__main__":
    for name in sorted(globals()):
        if name.startswith("test_"):
            globals()[name]()
            print("ok", name)
    print("all passed on", sys.implementation.name, time.time())
