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
from __future__ import print_function

def multiple_choice(prompt, choices, default, help_msg='No help available'):
	if len(choices) == 1:
		return ask_string(prompt, choices[0], help_msg)
	while True:
		print (prompt)
		i = 1
		for opt in choices:
			print (str(i)+". "+opt)
			i = i + 1
		input = raw_input("Your selection: ["+str(default)+"] ")
		if input is None or len(input)==0:
			return choices[default-1]
		if input == '?':
			print (help_msg)
			continue
		try:
			selection = int(input)
		except ValueError:
			print ("Please enter a number between 1 and "+str(len(choices)))
			continue
		if selection > len(choices) or selection < 1:
			print ("Please enter a number between 1 and "+str(len(choices)))
			continue
		return choices[selection-1]
def is_yes(input):
	return input in ['y', 'Y', 'true', 'True', 'yes']

def is_no(input):
	return input in ['n', 'N', 'false', 'False', 'no']

def ask_yesno(prompt, default=None, help_msg='No help available'):
	defstr = ''
	if default is not None:
		defstr = '[Y/n]' if default else '[y/N]'
	while True:
		input = raw_input(prompt+": "+defstr+" ")
		if input is None or len(input)==0:
			if default is None:
				continue
			return default
		if input == '?':
			print (help_msg)
			continue
		if is_yes(input):
			return True
		if is_no(input):
			return False
		print ("Please enter 'y' or 'n'")

def ask_matching(prompt, regex, default='', help_msg='No help available'):
	import re
	pattern = re.compile(regex)
	defstr = ' '
	if default is not None and len(default)>0:
		defstr = " ["+default+"] "
	while True:
		input = raw_input(prompt+defstr)
		if input is None or len(input)==0:
			return default
		if input == '?':
			print (help_msg)
			continue
		m = pattern.match(input)
		if m:
			return input
		if help_msg:
			print (help_msg)

def ask_string(prompt, default=None, help_msg='No help available'):
	defstr = ''
	if default is not None and len(default)>0:
		defstr = '['+default+']'
	while True:
		input = raw_input(prompt+": "+defstr+" ")
		if input is None or len(input)==0:
			if default is None:
				continue
			return default
		if input == '?':
			print (help_msg)
			continue
		return input

def ask_number(prompt, default=None, help_msg='No help available'):
	return ask_matching(prompt, '[0-9]+', default, help_msg)
