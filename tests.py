from django.test import TestCase

# Create your tests here.
import time
import random
import datetime
import logging
from django.test import TestCase
from django.utils import timezone
# Create your tests here.

from timers.utils import TimerManager

logger = logging.getLogger(__file__)


def test_sync(num, minute=3):
    """
    test timer tasks run Synchronously
    """
    now = timezone.now()
    now = now + datetime.timedelta(minutes=minute)
    now.replace(second=0)
    invoketime = now
    logger.info(f'//************ start {num} test timer, invoke time {invoketime} **************/')
    for i in range(num):
        TimerManager.timer_register("timers.tests.test_sync_callback", invoketime, "TEST_TASK", is_async=False)


def test_async(num, minute=3):
    """
    test timer tasks run with Asynchronous
    """
    now = timezone.now()
    now = now + datetime.timedelta(minutes=minute)
    now.replace(second=0)
    invoketime = now
    logger.info(f'//************ start  {num}  test timer, invoke time {invoketime} **************/')
    for i in range(num):
        TimerManager.timer_register("timers.tasks.test_async_callback", invoketime, "TEST_TASK", is_async=True)


def test_sync_callback():
    time.sleep(random.random()*4)
    logger.info(f"test sync timer callback function")
