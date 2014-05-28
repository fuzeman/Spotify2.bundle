import logging

log = logging.getLogger(__name__)


def log_progress(stream, label, position, last):
    """
    :type track: TrackReference
    """
    percent = float(position) / stream.length
    value = int(percent * 20)

    if value == last:
        return value

    log.debug('[%s] %s [%s|%s] %03d%%' % (
        stream.track.uri,
        label,
        (' ' * value),
        (' ' * (20 - value)),
        int(percent * 100)
    ))

    return value


def func_catch(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception, ex:
        log.error(ex)


def parse_range(value):
    if not value:
        return 0, None

    value = value.split('=')

    if len(value) != 2:
        return 0, None

    range_type, range = value

    if range_type != 'bytes':
        return 0, None

    range = range.split('-')

    if len(range) != 2:
        return 0, None

    return int(range[0] or 0), int(range[1]) if range[1] else None
