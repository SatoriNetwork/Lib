
import sys
import logging
from typing import Union, Callable
from satorilib.utils import colored, colors, styles

DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL


class ColoredFormatter(logging.Formatter):
    DEFAULT_COLOR_MAP = {
        logging.DEBUG: 'magenta',
        logging.INFO: 'blue',
        logging.WARNING: 'yellow',
        logging.ERROR: 'red',
        logging.CRITICAL: 'red',
    }
    DEFAULT_STYLE_MAP = {
        logging.DEBUG: None,
        logging.INFO: None,
        logging.WARNING: None,
        logging.ERROR: None,
        logging.CRITICAL: 'outlined',
    }

    def format(self, record):
        message = super(ColoredFormatter, self).format(record)
        return colored(
            message,
            color=getattr(
                record,
                'color',
                self.DEFAULT_COLOR_MAP.get(record.levelno, 'white')),
            style=getattr(
                record,
                'style', self.DEFAULT_STYLE_MAP.get(record.levelno)))


def setup(
    level=logging.DEBUG,
    file: Union[str, None] = None,
    format: str = None,
    stdoutAndFile: bool = False,
):
    formatter = ColoredFormatter(
        format or '%(asctime)s - %(levelname)s - %(message)s')
    if file is not None:
        file_handler = logging.FileHandler(file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        handlers = [file_handler, stream_handler] if stdoutAndFile else [
            file_handler]
    else:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        handlers = [stream_handler]
    logging.basicConfig(
        level=level,
        handlers=handlers)

    def log_unhandled_exception(exc_type, exc_value, exc_traceback):
        logging.critical("Unhandled exception", exc_info=(
            exc_type, exc_value, exc_traceback))
    sys.excepthook = log_unhandled_exception


def _log(fn: Callable, msg: str, color=None, style=None, *args, **kwargs):
    if color is not None or style is not None or kwargs.get('print'):
        if color in colors():
            printMsg = colored(
                msg,
                color=color,
                style=style if style in styles() else None)
        elif fn == logging.debug:
            printMsg = colored(
                msg,
                color='magenta',
                style=style if style in styles() else None)
        elif fn == logging.info:
            printMsg = colored(
                msg,
                color='blue',
                style=style if style in styles() else None)
        elif fn == logging.warning:
            printMsg = colored(
                msg,
                color='yellow',
                style=style if style in styles() else None)
        elif fn == logging.error:
            printMsg = colored(
                msg,
                color='red',
                style=style if style in styles() else None)
        elif fn == logging.critical:
            printMsg = colored(
                msg,
                color='red',
                style=style if style in styles() else 'outlined')
        print(printMsg)
    return fn(msg=msg, *args, **{k: v for k, v in kwargs.items() if k != 'print'})


def _getMsg(msgs):
    return ' '.join([str(m) for m in msgs])


def _getArgsKwargs(kwargs):
    args = []
    if 'args' in kwargs.keys():
        args = kwargs.pop('args')
    return args, kwargs


def debug(*msgs, color=None, style=None, **kwargs):
    args, kwargs = _getArgsKwargs(kwargs)
    return _log(logging.debug, _getMsg(msgs), *args, color=color, style=style, **kwargs)


def info(*msgs, color=None, style=None, **kwargs):
    args, kwargs = _getArgsKwargs(kwargs)
    return _log(logging.info, _getMsg(msgs), *args, color=color, style=style, **kwargs)


def warning(*msgs, color=None, style=None, **kwargs):
    args, kwargs = _getArgsKwargs(kwargs)
    return _log(logging.warning, _getMsg(msgs), *args, color=color, style=style, **kwargs)


def error(*msgs, color=None, style=None, **kwargs):
    args, kwargs = _getArgsKwargs(kwargs)
    return _log(logging.error, _getMsg(msgs), *args, color=color, style=style, **kwargs)


def critical(*msgs, color=None, style=None, **kwargs):
    args, kwargs = _getArgsKwargs(kwargs)
    return _log(logging.critical, _getMsg(msgs), *args, color=color, style=style, **kwargs)
