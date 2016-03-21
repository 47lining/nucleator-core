#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Code originated here: https://gist.github.com/cliffano/9868180
# There are, I believe, some tweaks by 47Lining
#
import time, os

from ansible.plugins.callback import CallbackBase

__metaclass__ = type

FIELDS = [
    'cmd',
    'command',
    'start',
    'end',
    'delta',
    'msg',
    'stdout',
    'stderr',
    ]

def human_log(res):
 
    if type(res) == type(dict()):
     	for field in FIELDS:
            if field in res.keys():         
                res_field = res[field]
                if isinstance(res_field, list):
                    res_field = ' '.join(res_field)
         
                print '{0}{1}:{0}{2}'.format(os.linesep, field, res_field.encode('utf-8') if isinstance(res_field, basestring) else res_field)	
		
class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'

    def __init__(self):
        super(CallbackModule, self).__init__()

    def on_any(self, *args, **kwargs):
        pass

    def runner_on_failed(
        self,
        host,
        res,
        ignore_errors=False,
        ):
        human_log(res)

    def runner_on_ok(self, host, res):
        human_log(res)

    def runner_on_error(self, host, msg):
        pass

    def runner_on_skipped(self, host, item=None):
        pass

    def runner_on_unreachable(self, host, res):
        human_log(res)

    def runner_on_no_hosts(self):
        pass

    def runner_on_async_poll(
        self,
        host,
        res,
        jid,
        clock,
        ):
        human_log(res)

    def runner_on_async_ok(
        self,
        host,
        res,
        jid,
        ):
        human_log(res)

    def runner_on_async_failed(
        self,
        host,
        res,
        jid,
        ):
        human_log(res)

    def playbook_on_start(self):
        pass

    def playbook_on_notify(self, host, handler):
        pass

    def playbook_on_no_hosts_matched(self):
        pass

    def playbook_on_no_hosts_remaining(self):
        pass

    def playbook_on_task_start(self, name, is_conditional):
        pass

    def playbook_on_vars_prompt(
        self,
        varname,
        private=True,
        prompt=None,
        encrypt=None,
        confirm=False,
        salt_size=None,
        salt=None,
        default=None,
        ):
        pass

    def playbook_on_setup(self):
        pass

    def playbook_on_import_for_host(self, host, imported_file):
        pass

    def playbook_on_not_import_for_host(self, host, missing_file):
        pass

    def playbook_on_play_start(self, pattern):
        pass

    def playbook_on_stats(self, stats):
        pass
