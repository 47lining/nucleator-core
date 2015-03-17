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

import ansible

from ansible.callbacks import vv
from ansible.errors import AnsibleError as ae
from ansible.runner.return_data import ReturnData
from ansible import utils
from ansible.utils import parse_kv, template
from ansible.inventory import Inventory
from ansible.inventory.host import Host
from ansible.inventory.group import Group

from boto.sts import STSConnection
from boto.sts.credentials import Credentials

import os
import sys

class ActionModule(object):
    ''' Create ssh-config from dynamic inventory with bastion proxy-commands '''

    ### Make sure runs once per play only
    BYPASS_HOST_LOOP = True
    TRANSFERS_FILES = False

    def __init__(self, runner):
        self.runner = runner


    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        try:
            args = {}
            if complex_args:
                args.update(complex_args)
            args.update(parse_kv(module_args))

            # get starting credentials
            # from environment:
            #   AWS_ACCESS_KEY_ID
            #   AWS_SECRET_ACCESS_KEY

            # use get started credentials to do the roles dance and obtain
            # temporary credentials in target account

            #target_role_name = 'init-test3-shoppertrak-NucleatorCageBuilder-1I5ZOAYRJLS8Z'

            data = {}
            data.update(inject)
    
            # TODO use nucleator facts instead
            source_role_name = data['nucleator_builder_role_name'] # TODO - RHS var here could have names in better alignment with current conventions
            target_role_name = data['cage_builder_role_name'] # TODO - RHS var here could have names in better alignment with current conventions

            print "Target Role Name: ", target_role_name
            print "Source Role Name: ", source_role_name

            source_account_id = data['source_account_number']
            target_account_id = data['target_account_number']

            print "Target Account Number: ", target_account_id
            print "Source Account Number: ", source_account_id

            try:
                envdict={}
                if self.runner.environment:
                    env=template.template(self.runner.basedir, self.runner.environment, inject, convert_bare=True)
                    env = utils.safe_eval(env)

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
                vv("Successfully assumed {0} role in account {1}".format(source_role_name, source_account_id))

            except Exception, e:
                result = dict(failed=True, msg=type(e).__name__ + ": Failed to obtain temporary credentials for role " + source_role_name + " in target account " + source_account_id + ", message: '" + str(e))
                return ReturnData(conn=conn, comm_ok=False, result=result)

            try:
                sts_connection = STSConnection(aws_access_key_id=source_role.credentials.access_key, aws_secret_access_key=source_role.credentials.secret_key, security_token=source_role.credentials.session_token)
                target_role = sts_connection.assume_role(role_arn='arn:aws:iam::{0}:role/{1}'.format(target_account_id, target_role_name), role_session_name='TargetRoleSession')
                vv("Successfully assumed {0} role in account {1}".format(target_role_name, target_account_id))
            
            except Exception, e:
                # deal with failure gracefully
                result = dict(failed=True, msg=type(e).__name__ + ": Failed to obtain temporary credentials for role " + target_role_name + " in target account " + target_account_id + ", message: '" + str(e)+ " Security_Token: " + source_role.credentials.session_token)
                return ReturnData(conn=conn, comm_ok=False, result=result)

        except Exception, e:
            # deal with failure gracefully
            result = dict(failed=True, msg=type(e).__name__ + ": " + str(e))
            return ReturnData(conn=conn, comm_ok=False, result=result)

        # create a result dict and package up results
        # return results 
        credentials = target_role.credentials
        bash_vars = "AWS_ACCESS_KEY_ID='{0}' AWS_SECRET_ACCESS_KEY='{1}' AWS_SECURITY_TOKEN='{2}'".format(credentials.access_key, credentials.secret_key, credentials.session_token)
        result = dict(failed=False, changed=True, bash_vars=bash_vars, aws_access_key_id=credentials.access_key, aws_secret_access_key=credentials.secret_key, aws_security_token=credentials.session_token)
	return ReturnData(conn=conn, comm_ok=True, result=result)
