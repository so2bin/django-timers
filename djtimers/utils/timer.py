#################################################################
#   timer implementation based on celery_beat
#   firstly only implement a timer with minute precision,
#   future can expand to secondly precision
#   @hebinbin 20180529
#
import logging
import uuid
import json
import datetime
import threading
from django.utils import timezone
from celery import shared_task
from celery import Celery

from pylibs.smart_import import smart_import
from djtimers.const import const
from djtimers.exceptions import TimerValidateError, TimerParameterError
from djtimers.const import TimerKlass

logger = logging.getLogger(__file__)


class TimerRunner(threading.Thread):
    """
    timer runner,  overwrite run function to implement multiple threading
    """
    __KEY_PREFIX = 'T'
    __MAX_KEY_LEN = 12 - len(__KEY_PREFIX)
    __is_async = "is_async"

    def __init__(self, is_async=True):
        super(TimerRunner, self).__init__()
        self.tkey = None
        self.callback = None
        self.invoketime = None
        self.ttype = None
        self.args = None
        self.kwargs = None
        self.invokeseconds = 0
        self.is_async = is_async  # 是否异步执行任务
        self._db_data = None

    @classmethod
    def get_timer_task_dao(cls):
        from djtimers.models import TimerTask
        return TimerTask.objects

    def run(self):
        """
        overwrite Thread.run, run as a threading
        """
        self.auto_call()

    def init_with_db(self, db_row):
        """
            initialization timer task from database row data

            db_row.kwargs has one key: "is_async" at least, this key is used in executor, will be pop before call callback
        """
        kwargs = json.loads(db_row.kwargs)
        is_async = kwargs.pop(self.__is_async, False) if kwargs else False

        self.callback = db_row.callback
        self.invoketime = db_row.invoketime
        self.invokeseconds = db_row.invokeseconds
        self.ttype = db_row.ttype
        self.tkey = db_row.tkey
        self.args = [] if not db_row.args else json.loads(db_row.args)
        self.kwargs = kwargs or {}
        self.is_async = is_async
        self._db_data = db_row
        return self

    def init(self, callback: str, invoketime, ttype: str, args=None, kwargs=None, invokeseconds=0):
        """
        initialization timer task
        process the invoke time with precision to 1 minute

        add is_async to kwargs, so kwargs has one key: "is_async" at least
        """
        callback_func = smart_import(callback)
        if not callable(callback_func):
            raise ValidateError(f'Invalid Timer callback: {callback}, Not Callable')
        # check callback is a shared_task
        if self.is_async and not isinstance(callback_func.app, Celery):
            raise ValidateError(f'Invalid Timer callback: {callback}, async model callback must be a Celery shared_task')
        if not isinstance(invoketime, datetime.datetime) or (args and not isinstance(args, (list, tuple, str))) \
                or (kwargs and not isinstance(kwargs, (dict, str))):
            raise ParameterError('Invalid Parameter')

        tkey = self.generate_tkey()
        ttype = self._generate_ttype_with_type(ttype)
        if timezone.is_naive(invoketime):
            invoketime = invoketime.astimezone(tz=timezone.get_current_timezone())
        # invoke time precision is 1 minute
        if invoketime.second != 0:
            invoketime = invoketime.replace(minute=invoketime.minute + 1, second=0, microsecond=0)
        if isinstance(args, (list, tuple)):
            args = json.dumps(args)
        # 将tkey添加到kwargs中
        if isinstance(kwargs, str):
            kwargs = json.loads(kwargs)
        kwargs = kwargs or {}
        kwargs['is_async'] = self.is_async
        if isinstance(kwargs, dict):
            kwargs = json.dumps(kwargs)

        self._db_data = self.get_timer_task_dao().create(tkey=tkey, ttype=ttype, invoketime=invoketime,
                             invokeseconds=invokeseconds, tklss=TimerKlass.T_NORMAL,
                             callback=callback, args=args, kwargs=kwargs)
        return self.init_with_db(self._db_data)

    @classmethod
    def init_from_tkey(cls, tkey):
        """init from tkey"""
        instance = cls()
        db_row = cls.get_timer_task_dao().filter(tkey=tkey).first()
        if not db_row:
            return None
        else:
            return instance.init_with_db(db_row)

    @classmethod
    def generate_tkey(cls):
        """generate timertask tkey"""
        while True:
            uid = uuid.uuid4().hex
            tkey = f'{cls.__KEY_PREFIX}{uid[0:cls.__MAX_KEY_LEN]}'
            if not cls.get_timer_task_dao().filter(tkey=tkey).exists():
                return tkey

    def _generate_ttype_with_type(self, _type: str):
        """generate ttype with type name"""
        return _type

    def call_sync(self):
        """
        call the callback functions
        """
        if not self._db_data or not self.callback:
            raise ValidateError('Invalid Timer to Run')
        callback = smart_import(self.callback)
        if not callable(callback):
            raise ValidateError(f'Invalid Timer callback: {self.callback}, Not Callable')
        self.update_to_running()
        logger.debug(f'run tasks {self.tkey} in sync model')
        return callback(*self.args, **self.kwargs)

    def call_async(self):
        """
            async call the callback functions
        """
        if not self._db_data or not self.callback:
            raise ValidateError('Invalid Timer to Run')
        callback = smart_import(self.callback)
        if not callable(callback):
            raise ValidateError(f'Invalid Timer callback: {self.callback}, Not Callable')
        self.update_to_running()
        logger.debug(f'run tasks {self.tkey} in async model')
        return callback.delay(*self.args, **self.kwargs)

    def auto_call(self):
        """
        call func with behavior of automatic using call_sync or call_async through "is_async" in "kwargs"
        """
        if not self._db_data or not self.callback:
            raise ValidateError('Invalid Timer to Run')
        callback = smart_import(self.callback)
        if not callable(callback):
            raise ValidateError(f'Invalid Timer callback: {self.callback}, Not Callable')
        if self.kwargs.get("is_async", False):
            return self.call_async()
        else:
            return self.call_sync()

    def update_to_running(self):
        self._db_data.status = const.TimerStatus.T_RUNNING
        self._db_data.save(update_fields=['status'])
        return self

    def update_to_failed(self):
        self._db_data.status = const.TimerStatus.T_FAILED
        self._db_data.last_run_time = timezone.now()
        self._db_data.run_times += 1
        self._db_data.save(update_fields=['status', 'last_run_time', 'run_times'])
        return self

    def update_to_stopped(self):
        self._db_data.status = const.TimerStatus.T_STOPPED
        self._db_data.last_run_time = timezone.now()
        self._db_data.run_times += 1
        self._db_data.save(update_fields=['status', 'last_run_time', 'run_times'])
        return self

    @classmethod
    def modify_timer(cls, tkey: str, **kwargs):
        """modify"""
        if kwargs:
            kwargs.pop('tkey', None)
        if not kwargs:
            return
        num = cls.get_timer_task_dao().filter(tkey=tkey).update(**kwargs)
        if not num:
            return
        return TimerRunner().init_from_tkey(tkey)

    @classmethod
    def delete_timer(cls, tkey: str):
        """delete"""
        return cls.get_timer_task_dao().filter(tkey=tkey).delete()
