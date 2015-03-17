# Copyright 2015 47Lining LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ansible.callbacks import display
import time

class CallbackModule(object):

    def format_time(self, value):
        func = lambda ll,b : list(divmod(ll[0],b)) + ll[1:]
        return "%d:%02d:%02d.%03d" % tuple(reduce(func,[[ value * 1000,], 1000,60,60]))

    def pad(self, value, padchar="*"):
        count = 78 - len(value)
        if count < 4:
            count = 4
        return "%s %s" % (value, padchar * count)
        
    def timestamp(self, underline=False):
        if not hasattr(self, 'start'):
            self.start = time.time()
            self.stamp = self.start
        time_now = time.time()
        formatted_dt = time.strftime('%A %d %B %Y  %H:%M:%S %z')
        last_elapsed = self.format_time(time_now - self.stamp)
        total_elapsed = self.format_time(time_now - self.start)
        self.stamp = time_now
        display(self.pad( '%s (%s)       %s' % (formatted_dt, last_elapsed, total_elapsed)))
        if underline:
            display("*" * 79)

    def playbook_on_task_start(self, name, is_conditional):
        self.timestamp(True)

    def playbook_on_setup(self):
        self.timestamp(False)

    def playbook_on_play_start(self, pattern):
        self.timestamp(True)

    def playbook_on_stats(self, stats):
        self.timestamp(True)

