import json
import boto
import yaml
import os
import time

from boto import configservice
from boto import s3
from boto import sns

from ansible.runner.return_data import ReturnData
from ansible.utils import parse_kv, template
from ansible import utils

class ActionModule(object):
    def __init__(self, runner):
        self.runner = runner

    def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        
		try:
			
			args = {}
			if complex_args:
				args.update(complex_args)
			args.update(parse_kv(module_args))

			role_name = args["role_name"]
			account_number = args["account_number"]
			region = args["region"]
			logging_bucket = args["log_bucket"]

			envdict={}
			if self.runner.environment:
				env=template.template(self.runner.basedir, self.runner.environment, inject, convert_bare=True)
				env = utils.safe_eval(env)

			bucketName = "config-bucket-%s" % account_number
			snsName = "config-topic-%s" % account_number
			
			s3_conn = s3.connect_to_region(region, aws_access_key_id=env.get("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=env.get("AWS_SECRET_ACCESS_KEY"),
                    security_token=env.get("AWS_SECURITY_TOKEN"))

			try:
				bucket = s3_conn.get_bucket(bucketName)
			except Exception, e:
				if(region == "us-east-1"):
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

			return ReturnData(conn=conn,
                comm_ok=True,
                result=dict(failed=False, changed=False, msg="Config Service Created"))

		except Exception, e:
			# deal with failure gracefully
			result = dict(failed=True, msg=type(e).__name__ + ": " + str(e))
			return ReturnData(conn=conn, comm_ok=False, result=result)

