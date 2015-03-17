#test_input_utils.py
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
import os, sys
sys.path.insert(0,'..')

import commands.utils.input_utils as INP

v = INP.multiple_choice("Select region", ['us-west-1', 'us-west-2', 'us-west-3'], 2)
print v

# v = INP.multiple_choice("Select region", ['us-west-1'], 1)
# print v

# v = INP.ask_yesno("Yes or no true?", True)
# print "true" if v else "false"

# v = INP.ask_yesno("Yes or no false?", False)
# print "true" if v else "false"

# v = INP.ask_yesno("Yes or no?")
# print "true" if v else "false"

# v = INP.ask_matching("Number no default no msg", "[0-9]+")
# print v

v = INP.ask_matching("Number One", "[0-9]+", default='0')
print v

v = INP.ask_matching("Number Two", "[0-9]+", '0', help_msg="Please enter a number")
print v

v = INP.ask_number("Number Two", '0', help_msg="Please enter a number")
print v

v = INP.ask_string("Hello", "goodbye", help_msg="aloha")
print v
