from utils import all
import logging
import os
import shutil


log = logging.getLogger('spotify2.migrator')


class Migrator(object):
    migrations = []

    @classmethod
    def register(cls, migration):
        cls.migrations.append(migration())

    @classmethod
    def run(cls):
        for migration in cls.migrations:
            log.debug('Running migration %s', migration)

            try:
                migration.run()
            except Exception, ex:
                log.warn('Migration failed - %s', ex)


class Migration(object):
    @property
    def code_path(self):
        return Core.code_path

    @property
    def libraries_path(self):
        return os.path.abspath(os.path.join(self.code_path, '..', 'Libraries'))

    @staticmethod
    def join_path(base, *args):
        path = os.path.join(base, *args)
        path = os.path.realpath(path)
        path = os.path.abspath(path)
        return path

    @staticmethod
    def delete_file(path, conditions=None):
        if not all([c(path) for c in conditions]):
            return False

        os.remove(path)
        return True

    @staticmethod
    def delete_directory(path, conditions=None):
        if not all([c(path) for c in conditions]):
            return False

        shutil.rmtree(path)
        return True


class Clean(Migration):
    tasks_code = [
        ('delete_file', [
            'plugin.py'
        ], os.path.isfile)
    ]

    tasks_libraries = [
        ('delete_directory', [
            'Shared/spotify_web'
        ], os.path.isdir)
    ]

    def run(self):
        self.execute(self.tasks_code, 'code', self.code_path)
        self.execute(self.tasks_libraries, 'libraries', self.libraries_path)

    def execute(self, tasks, name, base):
        for action, paths, conditions in tasks:
            if type(paths) is not list:
                paths = [paths]

            if type(conditions) is not list:
                conditions = [conditions]

            if not hasattr(self, action):
                log.warn('Unknown migration action "%s"', action)
                continue

            m = getattr(self, action)

            for path in [self.join_path(base, path) for path in paths]:
                log.debug('(%s) %s: "%s"', name, action, path)

                if not os.path.realpath(path).startswith(base):
                    log.debug('Ignoring action "%s" on "%s", path is outside of the base path "%s"', action, path, base)
                    continue

                if m(path, conditions):
                    log.debug('(%s) %s: "%s" - finished', name, action, path)


Migrator.register(Clean)


def run():
    Migrator.run()
