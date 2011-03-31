'''
Common utility functions
'''
from time import sleep


def wait_until_ready(objects, interval = 0.1):
    ''' Wait until Spotify model instances are ready to use '''
    instances = objects if not isinstance(objects, list) else list(objects)
    for instance in instances:
        while not instance.is_loaded():
            sleep(interval)
    return objects
