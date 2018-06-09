from django.db import models

# Create your models here.
import datetime
from django.db import models
from django.utils import timezone

from .const import TimerStatus, TimerKlass


class TimerTaskManager(models.Manager):
    def get_one_latest_waiting_task(self):
        """获取一个可执行的任务"""
        return self.filter(status=TimerStatus.T_WAITING).order_by("invoketime").first()

    def get_latest_runnable_tasks(self, num):
        """
        获取最新的num个可执行的定时器
        查询小于下一分钟的所有数据
        """
        now = timezone.now()
        next_minute_time = now.replace(minute=now.minute+1, second=0)
        rows = self.filter(status=TimerStatus.T_WAITING, invoketime__lt=next_minute_time).order_by("invoketime")
        return rows[:num]

    def get_latest_future_runnable_tasks(self):
        return self.filter(status=TimerStatus.T_WAITING, invoketime__gt=timezone.now()).order_by("invoketime").first()


class TimerTask(models.Model):
    """
    定时任务存储
    """

    class Meta:
        db_table = 'timer_tasks'
        index_together = (('invoketime', 'status'), )

    objects = TimerTaskManager()

    tkey = models.CharField(verbose_name='timer uid', max_length=32, unique=True)
    ttype = models.CharField(verbose_name='timer类型名', null=False, max_length=32)
    invoketime = models.DateTimeField(verbose_name='定时器触发时间(精确到分)', null=False)
    # 扩展后续精确到秒的定时器实现
    invokeseconds = models.IntegerField(verbose_name='定时器触发秒', default=0)
    callback = models.CharField(verbose_name='触发函数', null=False, max_length=128)
    args = models.TextField(verbose_name='参数json', default=None, null=True)
    kwargs = models.TextField(verbose_name='命名参数', default=None, null=True)
    status = models.IntegerField(verbose_name='状态', default=TimerStatus.T_WAITING)
    last_run_time = models.DateTimeField(verbose_name='上次触发时间', default=None, null=True)
    # timer类型，与ttype无关，1: 普通定时器 2: 周期定时器
    tklss = models.IntegerField(verbose_name='timer class', default=TimerKlass.T_NORMAL)
    run_times = models.IntegerField(verbose_name='总触发次数', default=0)
    cre_time = models.DateTimeField(verbose_name='创建时间', default=timezone.now)
    update_time = models.DateTimeField(verbose_name='更新时间', default=timezone.now)
