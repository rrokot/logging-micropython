from micropython import const
import io
import sys
import time

CRITICAL = const(50)
ERROR = const(40)
WARNING = const(30)
INFO = const(20)
DEBUG = const(10)
NOTSET = const(0)

_DEFAULT_LEVEL = const(WARNING)

_level_dict = {
    CRITICAL: "CRITICAL",
    ERROR: "ERROR",
    WARNING: "WARNING",
    INFO: "INFO",
    DEBUG: "DEBUG",
    NOTSET: "NOTSET",
}

_loggers = {}
_stream = sys.stderr
_default_fmt = "%(levelname)s:%(name)s:%(message)s"
_default_datefmt = "%Y-%m-%d %H:%M:%S"
_time_ns = getattr(time, "time_ns", None)
# A port whose time.time() gives whole seconds may have single precision floats, which keep
# the time of day to a minute at best: the time of a record stays an int there.
_float_time = isinstance(time.time(), float)


class LogRecord:
    def set(self, name, level, message):
        self.name = name
        self.levelno = level
        self.levelname = _level_dict[level]
        self.message = message
        if _time_ns:
            ns = _time_ns()
            self.msecs = ns // 1_000_000 % 1000
            self.ct = ns / 1_000_000_000 if _float_time else ns // 1_000_000_000
        else:
            self.ct = time.time()
            self.msecs = int((self.ct - int(self.ct)) * 1000)
        self.asctime = None


class Handler:
    def __init__(self, level=NOTSET):
        self.level = level
        self.formatter = None

    def close(self):
        pass

    def setLevel(self, level):
        self.level = level

    def setFormatter(self, formatter):
        self.formatter = formatter

    def format(self, record):
        if self.formatter:
            fmt = self.formatter
        else:
            fmt = _defaultFormatter
        return fmt.format(record)


class StreamHandler(Handler):
    def __init__(self, stream=None):
        super().__init__()
        self.stream = _stream if stream is None else stream
        self.terminator = "\n"

    def close(self):
        if hasattr(self.stream, "flush"):
            self.stream.flush()

    def emit(self, record):
        if record.levelno >= self.level:
            self.stream.write(self.format(record) + self.terminator)


class FileHandler(StreamHandler):
    def __init__(self, filename, mode="a", encoding="UTF-8"):
        super().__init__(stream=open(filename, mode=mode, encoding=encoding))

    def close(self):
        super().close()
        self.stream.close()


class Formatter:
    # What _strftime() knows: the directives of the default date format.
    _time_fields = {"%Y": (0, "%04d"), "%m": (1, "%02d"), "%d": (2, "%02d"),
                    "%H": (3, "%02d"), "%M": (4, "%02d"), "%S": (5, "%02d")}

    def __init__(self, fmt=None, datefmt=None):
        self.fmt = _default_fmt if fmt is None else fmt
        self.datefmt = _default_datefmt if datefmt is None else datefmt

    def usesTime(self):
        return "asctime" in self.fmt

    def formatTime(self, datefmt, record):
        if hasattr(time, "strftime"):
            return time.strftime(datefmt, time.localtime(record.ct))
        return self._strftime(datefmt, time.localtime(int(record.ct)))

    @classmethod
    def _strftime(cls, datefmt, t):
        # time.strftime() for MicroPython, which has none: %Y %m %d %H %M %S and %%; any other
        # directive stays as it is. A directive at a time, not a character: in Python that is
        # what a board pays for.
        if datefmt == _default_datefmt:
            return "%04d-%02d-%02d %02d:%02d:%02d" % t[:6]
        text = datefmt.replace("%%", "\0")   # %%Y is a %, then a Y
        for directive, (index, fmt) in cls._time_fields.items():
            if directive in text:
                text = text.replace(directive, fmt % t[index])
        return text.replace("\0", "%")

    def format(self, record):
        if self.usesTime():
            record.asctime = self.formatTime(self.datefmt, record)
        return self.fmt % {
            "name": record.name,
            "message": record.message,
            "msecs": record.msecs,
            "asctime": record.asctime,
            "levelname": record.levelname,
        }


#
#   The default formatter to use when no other is specified
#
_defaultFormatter = Formatter()


class Logger:
    def __init__(self, name, level=NOTSET):
        self.name = name
        self.level = level
        self.handlers = []
        self.record = LogRecord()

    def setLevel(self, level):
        self.level = level

    def isEnabledFor(self, level):
        return level >= self.getEffectiveLevel()

    def getEffectiveLevel(self):
        return self.level or getLogger().level or _DEFAULT_LEVEL

    @staticmethod
    def _traceback(exc_info):
        # The text of the exception exc_info names, in each of the ways CPython's logging takes it:
        # the exception itself, a sys.exc_info() tuple, or true for the one being handled. "" when
        # there is none, or when the port has no sys.exc_info() to tell which it is (ESP32 builds
        # have none): pass the exception itself there.
        if isinstance(exc_info, BaseException):
            exc = exc_info
        elif isinstance(exc_info, tuple):
            exc = exc_info[1]
        elif hasattr(sys, "exc_info"):
            exc = sys.exc_info()[1]
        else:
            exc = None
        if exc is None:
            return ""
        buf = io.StringIO()
        sys.print_exception(exc, buf)
        return buf.getvalue().rstrip("\n")

    # The level helpers pass their arguments on as a tuple, never as *args with exc_info=: a
    # call of that form, or a function with more state than fits the C stack, has MicroPython put
    # the function's state on the heap at each call, some 200 us on a board with PSRAM.
    def _log(self, level, msg, args, exc_info):
        if args:
            if isinstance(args[0], dict):
                args = args[0]
            msg = msg % args
        if exc_info:
            msg = self._with_traceback(msg, exc_info)
        self.record.set(self.name, level, msg)
        for h in self.handlers or getLogger().handlers:
            h.emit(self.record)

    def _with_traceback(self, msg, exc_info):
        text = self._traceback(exc_info)
        # as CPython has it: the traceback on the lines after the message
        return "%s\n%s" % (msg, text) if text else msg

    def log(self, level, msg, *args, exc_info=None):
        if self.isEnabledFor(level):
            self._log(level, msg, args, exc_info)

    def debug(self, msg, *args, exc_info=None):
        if self.isEnabledFor(DEBUG):
            self._log(DEBUG, msg, args, exc_info)

    def info(self, msg, *args, exc_info=None):
        if self.isEnabledFor(INFO):
            self._log(INFO, msg, args, exc_info)

    def warning(self, msg, *args, exc_info=None):
        if self.isEnabledFor(WARNING):
            self._log(WARNING, msg, args, exc_info)

    def error(self, msg, *args, exc_info=None):
        if self.isEnabledFor(ERROR):
            self._log(ERROR, msg, args, exc_info)

    def critical(self, msg, *args, exc_info=None):
        if self.isEnabledFor(CRITICAL):
            self._log(CRITICAL, msg, args, exc_info)

    def exception(self, msg, *args, exc_info=True):
        if self.isEnabledFor(ERROR):
            self._log(ERROR, msg, args, exc_info)

    def addHandler(self, handler):
        self.handlers.append(handler)

    def hasHandlers(self):
        return len(self.handlers) > 0


def getLogger(name=None):
    if name is None:
        name = "root"
    if name not in _loggers:
        _loggers[name] = Logger(name)
        if name == "root":
            basicConfig()
    return _loggers[name]


def _root_log(level, msg, args, exc_info):
    # As Logger's helpers: the arguments as a tuple, see Logger._log.
    root = getLogger()
    if root.isEnabledFor(level):
        root._log(level, msg, args, exc_info)


def log(level, msg, *args, exc_info=None):
    _root_log(level, msg, args, exc_info)


def debug(msg, *args, exc_info=None):
    _root_log(DEBUG, msg, args, exc_info)


def info(msg, *args, exc_info=None):
    _root_log(INFO, msg, args, exc_info)


def warning(msg, *args, exc_info=None):
    _root_log(WARNING, msg, args, exc_info)


def error(msg, *args, exc_info=None):
    _root_log(ERROR, msg, args, exc_info)


def critical(msg, *args, exc_info=None):
    _root_log(CRITICAL, msg, args, exc_info)


def exception(msg, *args, exc_info=True):
    _root_log(ERROR, msg, args, exc_info)


def shutdown():
    for k, logger in _loggers.items():
        for h in logger.handlers:
            h.close()
        _loggers.pop(logger, None)


def addLevelName(level, name):
    _level_dict[level] = name


def basicConfig(
        filename=None,
        filemode="a",
        format=None,
        datefmt=None,
        level=WARNING,
        stream=None,
        encoding="UTF-8",
        force=False,
):
    if "root" not in _loggers:
        _loggers["root"] = Logger("root")

    logger = _loggers["root"]

    if force or not logger.handlers:
        for h in logger.handlers:
            h.close()
        logger.handlers = []

        if filename is None:
            handler = StreamHandler(stream)
        else:
            handler = FileHandler(filename, filemode, encoding)

        handler.setLevel(level)
        handler.setFormatter(Formatter(format, datefmt))

        logger.setLevel(level)
        logger.addHandler(handler)


def getLevelName(level):
    # Like CPython: a level number gives its name, a level name gives its number, and
    # anything unknown gives "Level <value>". Names added by addLevelName are included.
    if level in _level_dict:
        return _level_dict[level]
    for number, name in _level_dict.items():
        if name == level:
            return number
    return "Level %s" % level


if hasattr(sys, "atexit"):
    sys.atexit(shutdown)
