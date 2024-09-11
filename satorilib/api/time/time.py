from typing import Union
import datetime as dt


def datetimeToTimestamp(time: dt.datetime) -> str:
    return time.strftime('%Y-%m-%d %H:%M:%S.%f')


def timestampToDatetime(time: str) -> dt.datetime:
    return dt.datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f') if '.' in time else dt.datetime.strptime(time, '%Y-%m-%d %H:%M:%S')


def datetimeToSeconds(time: dt.datetime) -> float:
    return time.replace(tzinfo=dt.timezone.utc).timestamp()


def secondsToDatetime(time: float) -> dt.datetime:
    return dt.datetime.fromtimestamp(time, tz=dt.timezone.utc)


def timestampToSeconds(time: str) -> float:
    return datetimeToSeconds(timestampToDatetime(time))


def secondsToTimestamp(time: float) -> str:
    return datetimeToTimestamp(secondsToDatetime(time))


def timeToTimestamp(time: Union[str, float, dt.datetime]) -> str:
    if isinstance(time, str):
        return time
    if isinstance(time, float):
        return secondsToTimestamp(time)
    if isinstance(time, dt.datetime):
        return datetimeToTimestamp(time)


def timeToDatetime(time: Union[str, float, dt.datetime]) -> dt.datetime:
    if isinstance(time, str):
        return timestampToDatetime(time)
    if isinstance(time, float):
        return secondsToDatetime(time)
    if isinstance(time, dt.datetime):
        return time


def timeToSeconds(time: Union[str, float, dt.datetime]) -> float:
    if isinstance(time, str):
        return timestampToSeconds(time)
    if isinstance(time, float):
        return time
    if isinstance(time, dt.datetime):
        return datetimeToSeconds(time)


def earliestDate() -> dt.datetime:
    return dt.datetime(1000, 1, 1)


def now() -> dt.datetime:
    return dt.datetime.utcnow()
    # return dt.datetime.now(dt.UTC)


def nowStr() -> str:
    # return str(now()).split('+')[0]
    return now().strftime('%Y-%m-%d %H:%M:%S.%f')


def timeIt(fn) -> float:
    import time
    then = time.time()
    fn()
    now = time.time()
    return now - then


def isValidTimestamp(time: str) -> bool:
    def tryTimeConvert():
        try:
            timestampToDatetime(time)
            return True
        except Exception as _:
            return False

    return isinstance(time, str) and 18 < len(time) < 27 and tryTimeConvert()


def isValidDate(date: str) -> bool:
    try:
        dt.datetime.strptime(date, '%Y-%m-%d')
        return True
    except ValueError:
        return False
