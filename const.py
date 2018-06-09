#############################################
#   constant
#

# 定时器在celery_beat中的name字段
CELERY_BEAT_TIMER_NAME = 'CELERY_BEAT_TIMER_NAME'
CELERY_BEAT_TIMER_FUNC = 'timers.tasks.periodic_timer_caller'


class TimerKlass(object):
    """定时器类别"""
    T_NORMAL = 1
    S_NORMAL = '普通定时器'
    T_INTERVAL = 2
    S_INTERVAL = '周期定时器'


class TimerStatus(object):
    """timer status"""
    T_WAITING = 0
    S_WAITING = 'WAITING'
    T_RUNNING = 1
    S_RUNNING = 'RUNNING'
    T_FAILED = 2
    S_FAILED = 'FAILED'
    T_SUCCESS = 3
    S_SUCCESS = 'SUCCESS'
    T_STOPPED = 4
    S_STOPPED = 'STOPPED'

    MAP = {
        T_WAITING: S_WAITING,
        T_RUNNING: S_RUNNING,
        T_FAILED: S_FAILED,
        T_SUCCESS: S_SUCCESS,
        T_STOPPED: S_STOPPED
    }
