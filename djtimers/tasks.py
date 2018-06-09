import logging
from celery import shared_task
from django.db import transaction, models

from .manager import TimerManager

logger = logging.getLogger(__file__)

#########################################################
#  THIS IS THE TIMER CALLER CELERY TRIGGER FUNCTION
#  !!! DO NOT NEED CHANGE THIS FUNCTION NORMALLY
#
@shared_task
def periodic_timer_caller(*args, **kwargs):
    """
    timer tasks claerr
    """
    TimerManager.periodic_timer_caller(*args, **kwargs)

#########################################################
#   follows are test functions
#
@shared_task
def test_async_callback():
    time.sleep(random.random()*4)
    logger.info(f'test async timer callback function')
