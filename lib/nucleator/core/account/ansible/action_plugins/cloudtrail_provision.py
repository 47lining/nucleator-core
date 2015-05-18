import boto
import os

from boto import cloudtrail

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

			account_number = args["account_number"]
			region = args["region"]
			cloudtrail_bucket = args["cloudtrail_bucket"]

			envdict={}
			if self.runner.environment:
				env=template.template(self.runner.basedir, self.runner.environment, inject, convert_bare=True)
				env = utils.safe_eval(env)

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
					result = connection.update_trail(cloudtrail_name, cloudtrail_bucket, include_global_service_events=False)
					result = connection.start_logging(cloudtrail_name)
				except Exception, e:
					result = connection.create_trail(cloudtrail_name, cloudtrail_bucket, include_global_service_events=False)
					result = connection.start_logging(cloudtrail_name)

			return ReturnData(conn=conn,
                comm_ok=True,
                result=dict(failed=False, changed=False, msg="Cloud Trail Service Started"))

		except Exception, e:
			# deal with failure gracefully
			result = dict(failed=True, msg=type(e).__name__ + ": " + str(e))
			return ReturnData(conn=conn, comm_ok=False, result=result)

