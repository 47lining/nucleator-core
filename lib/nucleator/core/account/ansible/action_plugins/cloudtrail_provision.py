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
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os

from ansible.plugins.action import ActionBase
from ansible.utils.boolean import boolean

import boto, os
from boto import cloudtrail

class ActionModule(ActionBase):

    # def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        
        try:

            args = {}
            args.update(self._task.args)

            account_number = args["account_number"]
            region = args["region"]
            cloudtrail_bucket = args["cloudtrail_bucket"]

            envdict={}
            if self._task.environment:
                env=self._task.environment[0]

            if region == "us-east-":
                other_regions = ["us-west-2", "eu-west-1"]
            else:
                if region == "us-west-2":
                    other_regions = ["us-east-1", "eu-west-1"]
                else:
                    other_regions = ["us-east-1", "us-west-2"]

            for connect_region in other_regions:    

                cloudtrail_name = "Cloudtrail-%s-%s" % (account_number, connect_region)

                connection = cloudtrail.connect_to_region(connect_region, aws_access_key_id=env.get("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=env.get("AWS_SECRET_ACCESS_KEY"),
                    security_token=env.get("AWS_SECURITY_TOKEN"))
                
                try:
                    connection.update_trail(cloudtrail_name, cloudtrail_bucket, include_global_service_events=False)
                    connection.start_logging(cloudtrail_name)
                except Exception, e:
                    connection.create_trail(cloudtrail_name, cloudtrail_bucket, include_global_service_events=False)
                    connection.start_logging(cloudtrail_name)

            result['failed']=False
            result['changed']=False
            result['msg']="Cloud Trail Service Started"
            return result

        except Exception, e:
            # deal with failure gracefully
            result['failed']=True
            result['msg']=type(e).__name__ + ": " + str(e)
            return result
