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

import ansible

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleError as ae
from ansible import utils
from graffiti_monkey.core import GraffitiMonkey

import os
import os.path
import sys
import time

class ActionModule(ActionBase):
    """
    An action plugin to deploy to propagate tags from ec2 instances to related EBS volumes and snapshots.
    """

    ### Make sure runs once per play only
    BYPASS_HOST_LOOP = True

    # def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        try:
            args = {}
            if complex_args:
                args.update(complex_args)
            args.update(parse_kv(module_args))

            data = {}
            data.update(inject)

            # Get the region associated with the target cage
            region = args["region"]


            class IndiscriminateMonkey(GraffitiMonkey):

                def __init__(self, region):
                    super(IndiscriminateMonkey, self).__init__(region)

                def tag_volume(self, volume):
                    instance_id = None
                    if volume.attach_data.instance_id:
                        instance_id = volume.attach_data.instance_id
                    device = None
                    if volume.attach_data.device:
                        device = volume.attach_data.device
                    instance_tags = self._get_resource_tags(instance_id)
                    tags_to_set = {}
                    for key, val in instance_tags.items():
                        # Dont propagate AWS-internal tags
                        if not key.startswith("aws:") and not key.startswith("elasticbeanstalk:"):
                            tags_to_set[key] = val
                    tags_to_set['instance_id'] = instance_id

                    print ("\n\n" + str(tags_to_set) + "\n\n")

                    self._set_resource_tags(volume, tags_to_set)
                    return True

                def tag_snapshot(self, snapshot):
                    volume_id = snapshot.volume_id
                    volume_tags = self._get_resource_tags(volume_id)
                    tags_to_set = {}
                    for key, val in volume_tags.items():
                        if not key.startswith("aws:") and not key.startswith("elasticbeanstalk:"):
                            tags_to_set[key] = val

                    print ("\n\n" + str(tags_to_set) + "\n\n")
                    self._set_resource_tags(snapshot, tags_to_set)
                    return True

            monkey = IndiscriminateMonkey(region)
            monkey.propagate_tags()

        except Exception as e:
            result['failed']=True
            result['msg']=type(e).__name__ + ": " + str(e)
            return result

        result['failed']=False
        result['changed']=True
        return result
