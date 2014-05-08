from threading import Event
import logging
import traceback

log = logging.getLogger(__name__)


class Emitter(object):
    __constructed = False
    __callbacks = None

    def ensure_constructed(self):
        if self.__constructed:
            return

        self.__callbacks = {}
        self.__constructed = True

    def __wrap(self, callback, *args, **kwargs):
        def wrap(func):
            callback(func=func, *args, **kwargs)
            return func

        return wrap

    def on(self, events, func=None, on_bound=None):
        if not func:
            # assume decorator, wrap
            return self.__wrap(self.on, events, on_bound=on_bound)

        if not isinstance(events, (list, tuple)):
            events = [events]

        log.debug('on(events: %s, func: %s)', repr(events), repr(func))

        self.ensure_constructed()

        for event in events:
            if event not in self.__callbacks:
                self.__callbacks[event] = []

            # Bind callback to event
            self.__callbacks[event].append(func)

        # Call 'on_bound' callback
        if on_bound:
            call_wrapper(on_bound)

        return self

    def once(self, event, func=None):
        if not func:
            # assume decorator, wrap
            return self.__wrap(self.once, event)

        log.debug('once(event: %s, func: %s)', repr(event), repr(func))

        def once_callback(*args, **kwargs):
            self.off(event, once_callback)
            func(*args, **kwargs)

        self.on(event, once_callback)

        return self

    def off(self, event=None, func=None):
        log.debug('off(event: %s, func: %s)', repr(event), repr(func))

        self.ensure_constructed()

        if event and event not in self.__callbacks:
            return self

        if func and func not in self.__callbacks[event]:
            return self

        if event and func:
            self.__callbacks[event].remove(func)
        elif event:
            self.__callbacks[event] = []
        elif func:
            raise ValueError('"event" is required if "func" is specified')
        else:
            self.__callbacks = {}

        return self

    def emit(self, event, *args, **kwargs):
        log.debug('emit(event: %s, args: %s, kwargs: %s)', repr(event), repr(args), repr(kwargs))

        self.ensure_constructed()

        if event not in self.__callbacks:
            return

        for callback in self.__callbacks[event]:
            call_wrapper(callback, args, kwargs, event)

        return self

    def emit_on(self, event, *args, **kwargs):
        func = kwargs.pop('func', None)

        if not func:
            # assume decorator, wrap
            return self.__wrap(self.emit_on, event, *args, **kwargs)

        log.debug('emit_on(event: %s, func: %s, args: %s, kwargs: %s)', repr(event), repr(func), repr(args), repr(kwargs))

        # Bind func from wrapper
        self.on(event, func)

        # Emit event (calling 'func')
        self.emit(event, *args, **kwargs)

    def pipe(self, events, other):
        if type(events) is not list:
            events = [events]

        log.debug('pipe(events: %s, other: %s)', repr(events), repr(other))

        self.ensure_constructed()

        for event in events:
            self.on(event, lambda *args, **kwargs: other.emit(event, *args, **kwargs))

        return self


def on(emitter, event, func=None):
    emitter.on(event, func)

    return {
        'destroy': lambda: emitter.off(event, func)
    }


def once(emitter, event, func=None):
    return emitter.once(event, func)


def off(emitter, event, func=None):
    return emitter.off(event, func)


def emit(emitter, event, *args, **kwargs):
    return emitter.emit(event, *args, **kwargs)


def call_wrapper(callback, args=None, kwargs=None, event=None):
    try:
        callback(*(args or ()), **(kwargs or {}))
        return True
    except Exception, e:
        log.warn('Exception raised in callback %s for event "%s" - %s', callback, event, traceback.format_exc())
        return False
