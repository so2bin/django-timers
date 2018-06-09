from django.apps import AppConfig


class TimersConfig(AppConfig):
    name = 'timers'

    def ready(self):
        # initial timer manager
        from . import TimerManager
        TimerManager.init_timer()
