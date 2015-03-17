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

import sys
import os
import argparse
import re

def validate_customer(customer_name):
    pattern = re.compile("^[a-z0-9-]+$")
    return None if pattern.match(customer_name) else "customer can contain only lowercase alpha characters, numbers and dashes"

def validate_account(account):
    pattern = re.compile("^[a-z0-9-]+$")
    return None if pattern.match(account) else "account can contain only lowercase alpha characters, numbers and dashes"

def validate_cage(cage_name):
    # TODO - is this the right regex?
    pattern = re.compile("^[a-z0-9-]+$")
    return None if pattern.match(cage_name) else "cage can contain only lowercase alpha characters, numbers and dashes"

class ValidateCustomerAction(argparse.Action):
    
    def __call__(self,parser,namespace,values,option_string=None):
        error_msg = validate_customer(values)
        if error_msg:
            parser.error(error_msg)
        else:
            setattr(namespace,self.dest,values)

class ValidateAccountAction(argparse.Action):

    def __call__(self,parser,namespace,values,option_string=None):
        error_msg = validate_account(values)
        if error_msg:
            parser.error(error_msg)
        else:
            setattr(namespace,self.dest,values)

w_stdout = sys.stdout.write
f_stdout = sys.stdout.flush
w_stderr = sys.stderr.write
f_stderr = sys.stdout.flush

verbose=False #TODO - get from cli invocation

def write_info(msg, force=False):
    if verbose or force:
        w_stdout('INFO: {0}{1}'.format(msg, os.linesep))
        f_stdout()

def write_err(msg, exit=True):
    w_stderr('ERROR: {0}{1}'.format(msg, os.linesep))
    if exit:
        sys.exit(1)

def write(msg, flush=True):
    w_stdout(msg)
    if flush:
        f_stdout()

def get_var(key, default=None, clean=False):
    value = os.environ.get(key, default)
    return (value.strip() if isinstance(value, basestring) and clean else value)

def get_clean(key, default=None):
    return get_var(key, default, True)
