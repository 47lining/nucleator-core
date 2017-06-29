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

# See for example ansible.plugins.action.add_host.py
from __future__ import print_function
try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()
from ansible.parsing.splitter import parse_kv
from ansible.template import template, safe_eval
from ansible.plugins.action import ActionBase

__metaclass__ = type

from ansible.errors import AnsibleError as ae
from ansible import utils
from ansible.inventory import Inventory
from ansible.inventory.host import Host
from ansible.inventory.group import Group

from boto.sts import STSConnection
from boto.sts.credentials import Credentials

import os
import sys

class ActionModule(ActionBase):
    ''' Create ssh-config from dynamic inventory with bastion proxy-commands '''

    ### Make sure runs once per play only
    BYPASS_HOST_LOOP = True
    TRANSFERS_FILES = False

    # def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        try:
            # get starting credentials
            # from environment:
            #   AWS_ACCESS_KEY_ID
            #   AWS_SECRET_ACCESS_KEY

            # use get started credentials to do the roles dance and obtain
            # temporary credentials in target account

            #target_role_name = 'init-test3-shoppertrak-NucleatorCageBuilder-1I5ZOAYRJLS8Z'

            data = {}
            data.update(self._task.args)
            data.update(task_vars)
            # sys.stderr.write(str(self._task.environment)+"\n")
            # sys.stderr.flush()
            # display.display(str(data))

            # TODO use nucleator facts instead
            source_role_name = data['nucleator_builder_role_name'] # TODO - RHS var here could have names in better alignment with current conventions
            target_role_name = data['cage_builder_role_name'] # TODO - RHS var here could have names in better alignment with current conventions

            print ("Target Role Name: ", target_role_name)
            print ("Source Role Name: ", source_role_name)

            source_account_id = data['source_account_number']
            target_account_id = data['target_account_number']

            print ("Target Account Number: ", target_account_id)
            print ("Source Account Number: ", source_account_id)

            try:
                envdict={}
                if self._task.environment:
                    env=self._task.environment[0]

                aws_access_key_id=env.get("AWS_ACCESS_KEY_ID")
                aws_secret_access_key=env.get("AWS_SECRET_ACCESS_KEY")
                security_token=env.get("AWS_SECURITY_TOKEN")

                aws_access_key_id = aws_access_key_id if aws_access_key_id else None
                aws_secret_access_key = aws_secret_access_key if aws_secret_access_key else None
                security_token = security_token if security_token else None

                sts_connection = STSConnection(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    security_token=security_token
                )
                source_role = sts_connection.assume_role(role_arn='arn:aws:iam::{0}:role/{1}'.format(source_account_id, source_role_name), role_session_name='SourceRoleSession')
                display.vv("Successfully assumed {0} role in account {1}".format(source_role_name, source_account_id))

            except Exception as e:
                result['failed']=True
                result['msg']=type(e).__name__ + ": Failed to obtain temporary credentials for role " + source_role_name + " in target account " + source_account_id + ", message: '" + str(e)
                return result

            try:
                sts_connection = STSConnection(aws_access_key_id=source_role.credentials.access_key, aws_secret_access_key=source_role.credentials.secret_key, security_token=source_role.credentials.session_token)
                target_role = sts_connection.assume_role(role_arn='arn:aws:iam::{0}:role/{1}'.format(target_account_id, target_role_name), role_session_name='TargetRoleSession')
                display.vv("Successfully assumed {0} role in account {1}".format(target_role_name, target_account_id))

            except Exception as e:
                # deal with failure gracefully
                result['failed']=True
                result['msg']=type(e).__name__ + ": Failed to obtain temporary credentials for role " + target_role_name + " in target account " + target_account_id + ", message: '" + str(e)+ " Security_Token: " + source_role.credentials.session_token
                return result

        except Exception as e:
            # deal with failure gracefully
            result['failed']=True
            result['msg']=type(e).__name__ + ": " + str(e)
            return result

        # create a result dict and package up results
        # return results
        credentials = target_role.credentials
        bash_vars = "AWS_ACCESS_KEY_ID='{0}' AWS_SECRET_ACCESS_KEY='{1}' AWS_SECURITY_TOKEN='{2}'".format(credentials.access_key, credentials.secret_key, credentials.session_token)
        result['failed']=False
        result['changed']=True
        result['bash_vars']=bash_vars
        result['aws_access_key_id']=credentials.access_key
        result['aws_secret_access_key']=credentials.secret_key
        result['aws_security_token']=credentials.session_token
        return result
