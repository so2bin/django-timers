from rest_framework.exceptions import APIException
from rest_framework import status
from django.utils.translation import ugettext_lazy as _


class TimersError(APIException):
    message = 'Timer Exceptions'
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _(message)


class TimerParameterError(TimersError):
    message = 'Parameter Error'


class TimerValidateError(TimersError):
    message = 'Validate Error'
