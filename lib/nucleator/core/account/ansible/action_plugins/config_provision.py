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
import json
import boto
import yaml
import os
import time
import traceback, sys
from boto import configservice
from boto import s3
from boto import sns

from ansible.plugins.action import ActionBase
from ansible import utils

class ActionModule(ActionBase):
    # def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        try:
            args = {}
            args.update(self._task.args)

            role_name = args["role_name"]
            account_number = args["account_number"]
            region = args["region"]
            logging_bucket = args["log_bucket"]

            envdict={}
            if self._task.environment:
                env=self._task.environment[0]

            bucketName = "config-bucket-%s" % account_number
            snsName = "config-topic-%s" % account_number

            s3_conn = s3.connect_to_region(region, aws_access_key_id=env.get("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=env.get("AWS_SECRET_ACCESS_KEY"),
                    security_token=env.get("AWS_SECURITY_TOKEN"))

            try:
                bucket = s3_conn.get_bucket(bucketName)
            except Exception as e:
                if(region is "us-east-1"):
                    bucket1 = s3_conn.create_bucket(bucketName)
                    bucket2 = s3_conn.get_bucket(logging_bucket)
                    response = bucket1.enable_logging(bucket2, "ConfigBucket/")
                else:
                    bucket1 = s3_conn.create_bucket(bucketName, location=region)
                    bucket2 = s3_conn.get_bucket(logging_bucket)
                    response = bucket1.enable_logging(bucket2, "ConfigBucket/")

            sns_conn = sns.connect_to_region(region, aws_access_key_id=env.get("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=env.get("AWS_SECRET_ACCESS_KEY"),
                    security_token=env.get("AWS_SECURITY_TOKEN"))

            sns_conn.create_topic(snsName)

            snsARN = "arn:aws:sns:%s:%s:%s" % (region, account_number, snsName)

            connection = configservice.connect_to_region(region, aws_access_key_id=env.get("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=env.get("AWS_SECRET_ACCESS_KEY"),
                    security_token=env.get("AWS_SECURITY_TOKEN"))

            response = connection.describe_configuration_recorders()

            if len(response["ConfigurationRecorders"]) is 0:
                recorder_name = "config-recorder-%s" % account_number
            else:
                for item in response["ConfigurationRecorders"]:
                    recorder_name = item["name"]

            response = connection.describe_delivery_channels()

            if len(response["DeliveryChannels"]) is 0:
                channel_name = "config-channel-%s" % account_number
            else:
                for item in response["DeliveryChannels"]:
                    channel_name = item["name"]

            ConfigurationRecorder={
                'name': recorder_name,
                'roleARN': "arn:aws:iam::%s:role/%s" % (account_number, role_name)
            }

            ConfigurationChannel={
                'name': channel_name,
                's3BucketName': bucketName,
                'snsTopicARN': snsARN
            }

            response = connection.put_configuration_recorder(ConfigurationRecorder)
            response = connection.put_delivery_channel(ConfigurationChannel)
            response = connection.start_configuration_recorder(recorder_name)

            result['failed']=False
            result['changed']=False
            result['msg']="Config Service Started"
            return result

        except Exception as e:
            # deal with failure gracefully
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print ("*** print_tb:")
            traceback.print_tb(exc_traceback, limit=1, file=sys.stderr)

            result['failed']=True
            result['msg']=type(e).__name__ + ": " + str(e)
            return result

