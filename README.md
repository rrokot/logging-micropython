# logging-micropython

A lightweight `logging` module for MicroPython that also runs unchanged on CPython,
so the same code can be tested on a desktop and deployed to a board.

It is a fork of [`logging`](https://github.com/micropython/micropython-lib/tree/master/python-stdlib/logging)
from [micropython-lib](https://github.com/micropython/micropython-lib).

## Differences from micropython-lib

- Works on regular Python, not only on MicroPython.
- `StreamHandler()` and `FileHandler()` work without `setFormatter()`, using the default format.
- `exception()` prints tracebacks on regular Python too; `exc_info=False` turns the traceback off.
- Adds `getLevelName()`: `getLevelName(40)` → `"ERROR"`, `getLevelName("ERROR")` → `40`.

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

## License

MIT, see [LICENSE](LICENSE). Based on micropython-lib, © micropython-lib contributors.
