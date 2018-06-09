# 基于django+celery的分钟级通用定时器实现
## 介绍
1. django中没有很好的定时器机制，celery自带的定时异步实现也有过期时间，好像是默认是2小时（详情可查看celery官网对`eta`参数的说明），无法作为一个通用定时器来用。
当然采用其它中间件来实现可能会更好，但这里直接使用django_celery_beta配合celery的CronScheduler机制来实现了一个通用定时器，
目前在实践使用中运行良好，但缺点是定时器精度只能精确到分钟级，没有实现秒级的精度，如果没有秒级或更高精度的需求，目前的实现也够用了。
2. 目前只实现了一次性执行的定时器，末实现周期型的定时器，定时精度为1分钟,定时器采用多线程执行，允许并行执行多个定时器。
回调函数允许异步执行，需要满足两个条件：1. 回调函数使用shared_task装饰，2. timer_register的参数is_async=True如果回调函数是同步执行，需要注意阻塞函数会阻塞定时器的执行

## API
* 定时器注册:  `TimerManager.timer_register`
    注册接口接收回调函数以及参数、定时器类型名等，提供`is_async`参数使用回调函数通过`celery`做异步执行， 推荐使用is_async执行函数，以防阻塞定时器。
* 修改： `TimerManager.timer_modify`
* 删除： `TimerManager.timer_delete`

## 安装
1. 与安装普通django app一样，下载到django项目中，把`timers`添加到`settings.py`的`INSTALLED_APPS`中；
2. 执行`python manager.py makemigrations timers`
3. 执行`python manager.py migrate`
