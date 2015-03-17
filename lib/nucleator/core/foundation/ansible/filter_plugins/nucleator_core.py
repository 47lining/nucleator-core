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

from __future__ import absolute_import

import string
import random
import os.path
import string
import hashlib
import re
import math

def aws_id_generator(filter_string, size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))

def s3safe(value):
    length = len(value)
    if length < 64:
        return value
    trunc = value[:38]
    hashed = hashlib.md5(value).hexdigest()
    hashed_integer = int(hashed, 16)
    base36 = toBase36(hashed_integer)
    return trunc + base36

def toBase36(num):
    b=36
    base = '0123456789abcdefghijklmnopqrstuvwxyz';
    r = num % b
    res = base[r];
    q = math.floor(num / b)
    while q:
        r = q % b
        q = math.floor(q / b)
        res = base[int(r)] + res
    return res
 
class FilterModule(object):
    ''' Nucleator jinja2 filters '''

    def filters(self):
        ''' return a dict mapping filter names to filter functions. '''
        return {
            # uuid-esque but safe for s3 keys
            'awsIdentifier': aws_id_generator,

            # make long names short enough for s3 by hashing them
            's3safe': s3safe,

            # make os-safe filesystem paths from multiple components
            'osPathJoin': os.path.join,

            # split string on provided substring
            'stringSplit': string.split,

            # escape contents to make string regex safe
            'regex_escape': re.escape,

        }
