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
