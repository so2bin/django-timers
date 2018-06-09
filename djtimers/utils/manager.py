#########################################################
#   timer register and clear functions
#
import json
import logging
import datetime
from functools import wraps
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule, PeriodicTasks
from django.db import transaction
from celery import shared_task

from . import const
from .timer import TimerRunner
from .executor import BatchTimerExecutor
from .exceptions import TimerParameterError, TimerValidateError

logger = logging.getLogger(__file__)


class TimerManager(object):
    """
    timer manager, provide timer register, caller, modify, delete api.
    """
    @classmethod
    def get_timer_task_dao(cls):
        from djtimers.models import TimerTask
        return TimerTask.objects

    @classmethod
    def get_latest_future_tasks(cls):
        """latest one of future runnable task"""
        return cls.get_timer_task_dao().get_latest_future_runnable_tasks()

    @staticmethod
    def _new_periodic(task):
        """
        :param task: TimerRunner instance
        :return:
        """
        schedule = CrontabSchedule.objects.create(
            month_of_year=task.invoketime.month, day_of_month=task.invoketime.day,
            day_of_week='*', hour=task.invoketime.hour, minute=task.invoketime.minute
        )
        perid_kwargs = {
            'year': task.invoketime.year,
            'is_running': False  # 是否正在执行定时器
        }
        return PeriodicTask.objects.create(
            crontab=schedule, name=const.CELERY_BEAT_TIMER_NAME, task=const.CELERY_BEAT_TIMER_FUNC,
            kwargs=json.dumps(perid_kwargs)
        )

    @staticmethod
    def _update_cron_timer(period_task, invoketime):
        """
        更新定时器时间
        如果invoketime小于等于now则使用下一分钟
        """
        now = timezone.now()
        now = now.replace(second=0, microsecond=0)
        if invoketime <= now:
            invoketime = now + datetime.timedelta(minutes=2)
        cron = period_task.crontab
        kwargs = json.loads(period_task.kwargs)
        # check next timer may be invoked in next year
        if int(kwargs['year']) != invoketime.year:
            kwargs['year'] = invoketime.year
            period_task.kwargs = json.dumps(kwargs)
            period_task.save(update_fields=['kwargs'])
        CrontabSchedule.objects.filter(id=cron.id)\
            .update(month_of_year=invoketime.month, day_of_month=invoketime.day,
                    day_of_week='*', hour=invoketime.hour, minute=invoketime.minute)
        # 更新shcedulers
        PeriodicTasks.objects.filter(ident=1).update(last_update=now)

    @staticmethod
    def periodic_timer_caller(*args, **kwargs):
        """
        call this function when celery-beat periodic task is triggered
        """
        if not kwargs:
            raise ParameterError('timeout task parameter: kwargs error')
        if 'year' not in kwargs:
            raise ParameterError('timeout task parameter must include: year')
        # 检查跨年
        now = timezone.now()
        if now.year != kwargs['year']:
            return
        try:
            kwargs['is_running'] = True
            PeriodicTask.objects.filter(name=const.CELERY_BEAT_TIMER_NAME).update(kwargs=json.dumps(kwargs))
            # 执行函数
            BatchTimerExecutor().run()
        except Exception as e:
            logger.error(f'timer run time error: {e.message}')
        finally:
            kwargs['is_running'] = False
            PeriodicTask.objects.filter(name=const.CELERY_BEAT_TIMER_NAME).update(kwargs=json.dumps(kwargs))

    @staticmethod
    def cron_to_datetime(cron):
        now = timezone.now().astimezone(tz=timezone.UTC())
        cron_year = now.year
        cron_month = now.monty if cron.month_of_year == '*' else int(cron.month_of_year)
        cron_day = now.monty if cron.day_of_month == '*' else int(cron.day_of_month)
        cron_minute = now.monty if cron.minute == '*' else int(cron.minute)
        cron_hour = now.monty if cron.hour == '*' else int(cron.hour)
        cron_task_time = datetime.datetime(cron_year, cron_month, cron_day, cron_hour, cron_minute,
                                           second=0, tzinfo=timezone.UTC())
        return cron_task_time

    @staticmethod
    def timer_register(callback: str, invoketime, ttype, args=None, kwargs=None, invokeseconds=0, is_async=False):
        """
        timer register
        invoke time precision is one minute
        check whether CELERY_BEAT_TIMER_NAME periodic task exist
        if not exists, create new one
        if exists, check and update crontab time

        is_async=True will block the timer executor while running, not recommend for long-time functions
        :param callback:
        :param invoketime:
        :param ttype:
        :param args:
        :param kwargs:
        :param invokeseconds:
        :param is_async: whether run func asynchronously
        :return:
        """
        task = TimerRunner(is_async=is_async).init(callback, invoketime, ttype, args, kwargs, invokeseconds=invokeseconds)
        period_task = None
        try:
            period_task = PeriodicTask.objects.get(name=const.CELERY_BEAT_TIMER_NAME)
        except PeriodicTask.DoesNotExist:
            period_task = TimerManager._new_periodic(task)
        finally:
            # 更新定时器
            latest_task = TimerManager.get_timer_task_dao().get_one_latest_waiting_task()
            TimerManager._update_cron_timer(period_task, latest_task.invoketime)
            TimerManager.start_periodic_timer()

    @staticmethod
    def flush_timer():
        """
        flush timer cron scheduler with latest invoke time
        :return: False: Timer is ready, True: Timer is close or have none Timer
        """
        try:
            period_task = PeriodicTask.objects.get(name=const.CELERY_BEAT_TIMER_NAME)
        except PeriodicTask.DoesNotExist:
            return False
        else:
            # 更新定时器
            latest_task = TimerManager.get_timer_task_dao().get_one_latest_waiting_task()
            if not latest_task:
                TimerManager.stop_periodic_timer()
                return False
            else:
                TimerManager._update_cron_timer(period_task, latest_task.invoketime)
                TimerManager.start_periodic_timer()
                return True

    @staticmethod
    def timer_modify(tkey: str, **kwargs):
        """
        modify timer task
        """
        runner = TimerRunner().modify_timer(tkey, **kwargs)
        TimerManager.flush_timer()

    @staticmethod
    def timer_delete(tkey: str):
        """
        delete timer task
        """
        TimerRunner().delete_timer(tkey)
        TimerManager.flush_timer()

    @staticmethod
    def start_periodic_timer():
        PeriodicTask.objects.filter(name=const.CELERY_BEAT_TIMER_NAME).update(enabled=True)

    @staticmethod
    def stop_periodic_timer():
        PeriodicTask.objectsfilter(name=const.CELERY_BEAT_TIMER_NAME).update(enabled=False)

    @staticmethod
    def try_next_to_future_timer():
        """
        try to set the timer
        """
        future_task = TimerManager.get_latest_future_tasks()
        if not future_task:
            return False
        else:
            period_task = PeriodicTask.objects.filter(name=const.CELERY_BEAT_TIMER_NAME).select_related('crontab').first()
            TimerManager._update_cron_timer(period_task, future_task.invoketime)
            return True

    @staticmethod
    def init_timer():
        """
        run at the begin of server, initial the timer cron time in CrontabSchedule with the latest timertask

        will called while server starting, use default database
        """
        TimerManager.flush_timer()
