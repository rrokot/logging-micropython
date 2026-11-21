"""For a quick run of the tests on CPython with pytest: what logging.py takes from MicroPython.

logging.py is MicroPython's alone; CPython lacks the micropython module and sys.print_exception.
"""
import sys
import traceback
import types

sys.modules.setdefault("micropython", types.SimpleNamespace(const=lambda value: value))
if not hasattr(sys, "print_exception"):
    sys.print_exception = lambda exc, file: traceback.print_exception(type(exc), exc, exc.__traceback__, file=file)
