###############################################
#   timer executors
#
import logging
import datetime
import threading
from django.utils import timezone
from django.db import transaction

from .timer import TimerRunner

logger = logging.getLogger(__file__)

# BatchTimerExecutor run concurrent timer number
DEFAULT_NUM_BATCH_PARALLEL = 5


class BaseTimerExecutor(object):
    """Abstract executor"""
    def __init__(self):
        pass

    def run(self):
        raise NotImplementedError()


class BatchTimerExecutor(BaseTimerExecutor):
    """
    batch timers task executor
    DEFAULT_NUM_BATCH_PARALLEL: the parallel run number of timer tasks once tick
    """
    def __init__(self, con_num=DEFAULT_NUM_BATCH_PARALLEL, bthread=True):
        """
        :param con_num: concurrent timer number
        """
        super(BatchTimerExecutor, self).__init__()
        self._concurrent_num = con_num
        self._use_thread = bthread

    @classmethod
    def get_timer_task_dao(cls):
        from djtimers.models import TimerTask
        return TimerTask.objects

    def get_latest_runnable_tasks(self):
        """get latest runnable tasks with con_num"""
        return self.get_timer_task_dao().get_latest_runnable_tasks(self._concurrent_num)

    def get_latest_future_tasks(self):
        """latest one of future runnable task"""
        return self.get_timer_task_dao().get_latest_future_runnable_tasks()

    def run_as_thread(self, runner):
        """
        run task as a thread, return thread object
        """
        return self.safe_call(runner, runner.start)

    def safe_call(self, runner, caller):
        """
        call function with catching exceptions
        """
        if not callable(caller) or not runner:
            return
        try:
            ret = caller()
        except Exception:
            logger.error(f'Timer Run Error | tkey: {runner.tkey}, callback: {runner.callback}, async: {runner.is_async}')
            runner.update_to_failed()
        else:
            runner.update_to_stopped()
            logger.info(f'timer task: {runner.tkey} run succeed, return: {ret}')

    def _run_one_by_one(self):
        """
        run the tasks once by one
        """
        count = 0
        logger.debug(f'running tasks one by one')
        for timer_task in self.get_latest_runnable_tasks():
            runner = TimerRunner().init_with_db(timer_task)
            self.safe_call(runner, runner.auto_call)
            count += 1
        return count

    def _run_parallel(self):
        """
        run tasks with multi threading
        """
        tasks = []
        count = 0
        logger.debug(f'running tasks with multi threads parallel')
        for timer_task in self.get_latest_runnable_tasks():
            runner = TimerRunner().init_with_db(timer_task)
            self.run_as_thread(runner)
            tasks.append(runner)
            count += 1
        for task in tasks:
            task.join()
        return count

    def run(self):
        """
        run tasks
        """
        from .manager import TimerManager
        begin_tick = timezone.now().timestamp() * 1000
        logger.debug(f'------------- begin timer running ----------------')
        while True:
            tasks = self.get_latest_runnable_tasks()
            if not tasks:
                if not TimerManager.try_next_to_future_timer():
                    TimerManager.stop_periodic_timer()
                break
            else:
                start_tick = timezone.now().timestamp() * 1000
                logger.debug(f'begin run timertasks, tasks length: {len(tasks)}')
                if self._use_thread:
                    self._run_parallel()
                else:
                    self._run_one_by_one()
                once_tick = timezone.now().timestamp() * 1000
                logger.debug(f'end one round, total millsec: {once_tick - start_tick}ms')
        end_tick = timezone.now().timestamp() * 1000
        logger.debug(f'------- end timer, total {end_tick - begin_tick}ms ----------')


class IntervalTimerExecutor(BaseTimerExecutor):
    """
    intverval timer executor    TODO NOT IMPLEMENTED NOW
    """
    def run(self):
        pass
