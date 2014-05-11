import logging

log = logging.getLogger(__name__)


def log_progress(track, label, position, last):
    """
    :type track: TrackReference
    """
    percent = float(position) / track.stream_length
    value = int(percent * 20)

    if value == last:
        return value

    log.debug('[%s] %s [%s|%s] %03d%%' % (
        track.uri,
        label,
        (' ' * value),
        (' ' * (20 - value)),
        int(percent * 100)
    ))

    return value
