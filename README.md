# logging-micropython

A lightweight `logging` module for MicroPython that behaves like CPython's, so code written
for CPython's `logging` runs on a board unchanged.

It is a fork of [`logging`](https://github.com/micropython/micropython-lib/tree/master/python-stdlib/logging)
from [micropython-lib](https://github.com/micropython/micropython-lib).

## Differences from micropython-lib

Each one makes it do what CPython's `logging` does:

- `StreamHandler()` and `FileHandler()` work without `setFormatter()`, using the default format.
- `%(asctime)s` works on MicroPython too, which has no `time.strftime()`: the date format may use
  `%Y %m %d %H %M %S` and `%%` there (the default one does).
- `%(msecs)d` comes from `time.time_ns()`, so it is right on a board whose `time.time()` gives
  whole seconds.
- `exc_info=` on `log()`, `debug()` … `critical()`, as in CPython: an exception, a
  `sys.exc_info()` tuple, or `True` for the one being handled; its traceback follows the message
  in the same record. `exception()` is one record too, and `exc_info=False` turns its traceback
  off. A MicroPython build without `sys.exc_info()` cannot tell which exception `True` means:
  pass the exception itself there (`log.error("failed", exc_info=e)`).
- Adds `getLevelName()`: `getLevelName(40)` → `"ERROR"`, `getLevelName("ERROR")` → `40`.

A logger keeps one record and fills it anew for each message, as micropython-lib's does: a
handler that keeps records instead of writing them out has to copy what it needs.

## Installation

Copy `logging.py` to the board, for example with
[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html):

```sh
mpremote cp logging.py :
```

## Usage

```python
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("sensor")

log.info("temperature %.1f", 21.5)

try:
    1 / 0
except ZeroDivisionError:
    log.exception("reading failed")
```

Supported: `getLogger`, `basicConfig`, `StreamHandler`, `FileHandler`, `Formatter`
(`%(asctime)s`, `%(msecs)d`, `%(levelname)s`, `%(name)s`, `%(message)s`),
`addLevelName`, `getLevelName` and the level helpers `debug` … `critical`, `exception`.

## Tests

```sh
mpremote mount . run tests/test_logging.py # on a board, importing ./logging.py
micropython tests/test_logging.py          # on the unix port
python -m pytest tests                     # a quick check on CPython
```

`logging.py` is MicroPython's alone; for the run on CPython, `tests/conftest.py` stands in for
what CPython lacks (the `micropython` module, `sys.print_exception`).

## License

MIT, see [LICENSE](LICENSE). Based on micropython-lib, © micropython-lib contributors.
