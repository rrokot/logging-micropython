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
except ZeroDivisionError as e:
    log.exception("reading failed")              # as on CPython, where the port has sys.exc_info()
    log.exception("reading failed", exc_info=e)  # everywhere, ESP32 builds included
```

Supported: `getLogger`, `basicConfig`, `StreamHandler`, `FileHandler`, `Formatter`
(`%(asctime)s`, `%(msecs)d`, `%(levelname)s`, `%(name)s`, `%(message)s`), `addLevelName`,
`getLevelName`, and `log()`, `debug()` … `critical()`, `exception()`, on a logger and as the
module's functions.

Not there yet, and code for CPython that uses it fails: `NullHandler`, the keywords `extra=`,
`stack_info=` and `stacklevel=`, the format fields `%(levelno)s`, `%(created)f`, `%(module)s`,
`%(lineno)d` and `%(funcName)s`, `removeHandler()`, filters, `logging.disable()`, and the
hierarchy of loggers (`getLogger("a.b")` takes nothing from `"a"`; no `getChild()`).

## Cost

Measured on an ESP32-S3 with 8 MiB of PSRAM, MicroPython 1.29, against micropython-lib's 0.6.2
(a call each, to a handler that writes nowhere):

| Call | micropython-lib | this fork |
|---|---|---|
| `debug()` below the level | 58 us | 36 us |
| `info()`, the default format | 1071 us | 1122 us |
| `info()` with `%(asctime)s` | 1063 us (writes `None`) | 1445 us |
| `exception(exc_info=e)` | 2789 us (two records) | 2601 us |
| heap a record takes | 288 bytes | 336 bytes (`time_ns()` for the msecs) |

The level helpers hand their arguments on as a tuple: on MicroPython a call that passes `*args`
together with a keyword, or a function with more state than fits the C stack, has its state put
on the heap at each call, some 200 us on a board with PSRAM.

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
