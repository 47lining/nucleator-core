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

import threading, sys
import subprocess as sp
from subprocess import PIPE

class ThreadWorker(threading.Thread):
    def __init__(self, callable, *args, **kwargs):
        super(ThreadWorker, self).__init__()
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
        self.setDaemon(True)

    def run(self):
        try:
            retval = self.callable(*self.args, **self.kwargs)
            return retval
        except Exception, e:
            print e

class Worker(object):

    def __init__(self):
        self.outlines=[]

    def work(self, pipe):
        while True:
            line = pipe.readline()
            if line == '':
                break
            else:
                sys.stdout.write(line)
                sys.stdout.flush
                self.outlines.append(line)

    def get_output(self):
        return ''.join(self.outlines)

class Popen(object):
    """
    Limited wrapper for subprocess.Popen, provides unbuffered output and recording for return of stdout, stderr and returncode upon completion of child process.

    Providing stdin to the child process is not currently supported.
    """

    def __init__(self, args, **kwargs):

        self.stdout=None
        self.stderr=None
        self.returncode=None

        self.child = sp.Popen(args, **kwargs)
    
        self.stdout_worker = Worker()
        self.stdout_thread = ThreadWorker(self.stdout_worker.work, self.child.stdout)

        self.stderr_worker = Worker()
        self.stderr_thread = ThreadWorker(self.stdout_worker.work, self.child.stderr)

        self.stdout_thread.start()
        self.stderr_thread.start()

    def communicate(self):
        for t in [self.stdout_thread, self.stderr_thread]:
            t.join()

        self.returncode = self.child.wait()
        self.stdout = self.stdout_worker.get_output()
        self.stderr = self.stderr_worker.get_output()
        return (self.stdout, self.stderr)
