import logging
import traceback

log = logging.getLogger(__name__)


def log_progress(stream, label, position, last):
    """
    :type track: TrackReference
    """
    percent = float(position) / stream.content_length
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
        log.error(traceback.format_exc())


def parse_range(value):
    if not value:
        return None

    value = value.split('=')

    if len(value) != 2:
        return None

    unit, value = value

    if unit != 'bytes':
        return None

    parts = value.split('-')

    if len(parts) != 2:
        return None

    return int(parts[0] or 0), int(parts[1]) if parts[1] else None


def parse_content_range(value):
    if not value:
        return None

    # Get unit
    value = value.split(' ')

    if len(value) != 2:
        return None

    unit, value = value

    # Validate unit
    if unit != 'bytes':
        return None

    # Get Total-Length
    parts = value.split('/')

    if len(parts) != 2:
        return None

    value, length = parts

    # Get Range
    parts = value.split('-')

    if len(parts) != 2:
        return None

    start, end = parts

    # Return result
    return int(start), int(end), int(length)
