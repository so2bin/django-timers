from django.apps import AppConfig


class DJTimersConfig(AppConfig):
    name = 'djtimers'

    def ready(self):
        # initial timer manager
        from . import TimerManager
        TimerManager.init_timer()
