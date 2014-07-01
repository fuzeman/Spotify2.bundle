from settings import LOGGERS

import logging

# Create "TRACE" level
logging.TRACE = 9
logging.addLevelName(logging.TRACE, 'TRACE')


class PlexHandler(logging.StreamHandler):
    level_funcs = {
        logging.DEBUG: Log.Debug,
        logging.INFO: Log.Info,
        logging.WARNING: Log.Warn,
        logging.ERROR: Log.Error,
        logging.CRITICAL: Log.Critical
    }

    def emit(self, record):
        func = self.level_funcs.get(record.levelno, Log.Debug)

        func('[%s] %s' % (record.name, self.format(record)))


def setup():
    Log.Debug(logging.Logger.manager.loggerDict.keys())

    logging.basicConfig(level=logging.DEBUG)

    logger_levels = levels()
    Log.Debug(logger_levels)

    for name in LOGGERS:
        level = logger_levels.get(name, logging.DEBUG)
        logger = logging.getLogger(name)

        logger.setLevel(level)
        logger.handlers = [PlexHandler()]

        Log.Debug('Piping events from "%s" to plex (level: %s)' % (name, logging.getLevelName(level)))


def levels():
    return {
        'plugin':    parse_level(Prefs['level_streaming']),
        'pyemitter': parse_level(Prefs['level_events'])
    }


def parse_level(name):
    if name == 'DEBUG':
        return logging.DEBUG

    if name == 'TRACE':
        return logging.TRACE

    return logging.INFO
