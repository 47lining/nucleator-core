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
from ansible.parsing.splitter import parse_kv
from ansible.template import template, safe_eval
from ansible.plugins.action import ActionBase

from ansible.errors import AnsibleError as ae
# from ansible import utils
from ansible.utils.hashing import checksum_s
from ansible.inventory import Inventory
from ansible.inventory.host import Host
from ansible.inventory.group import Group
import ansible.constants as C

import os, json, traceback, sys

class ActionModule(ActionBase):
    ''' Create ssh-config from dynamic inventory with bastion proxy-commands '''

    ### Make sure runs once per play only
    BYPASS_HOST_LOOP = True
    TRANSFERS_FILES = True

    def get_checksum(self, dest, all_vars, try_directory=False, source=None, tmp=None):
        try:
            dest_stat = self._execute_remote_stat(dest, all_vars=all_vars, follow=False, tmp=tmp)

            if dest_stat['exists'] and dest_stat['isdir'] and try_directory and source:
                base = os.path.basename(source)
                dest = os.path.join(dest, base)
                dest_stat = self._execute_remote_stat(dest, all_vars=all_vars, follow=False, tmp=tmp)

        except AnsibleError:
            return dict(failed=True, msg=to_native(get_exception()))

        return dest_stat['checksum']

    def build_customers(self, task_vars):
        # 'ansible_play_hosts_all': [u'bastion.build.test4.47lining.com', u'nat.build.test4.47lining.com']
        # 'ansible_play_hosts': [u'bastion.build.test4.47lining.com', u'nat.build.test4.47lining.com']
        # 'ansible_current_hosts': [u'bastion.build.test4.47lining.com', u'nat.build.test4.47lining.com']
        # 'play_hosts': [u'bastion.build.test4.47lining.com', u'nat.build.test4.47lining.com']
        # determine hosts in each cage for each customer
        customers={}
        for host in task_vars['ansible_play_hosts']:    # self.runner.host_set:
            data = {}
            data.update(task_vars)
            data.update(task_vars['hostvars'][host])

            # TODO use nucleator facts instead
            if 'ec2_tag_NucleatorCustomer' in data:
                customer_name = data['ec2_tag_NucleatorCustomer']
            else:
                customer_name="None"

            # TODO use nucleator facts instead
            if 'ec2_tag_NucleatorCage' in data:
                cage_name = data['ec2_tag_NucleatorCage']
            else:
                cage_name=data['ec2_tag_Name'].split("-")[1] if 'ec2_tag_Name' in data else "None"

            if customer_name not in customers:
                customers[customer_name]={}
            if cage_name not in customers[customer_name]:
                customers[customer_name][cage_name]=[]

            customers[customer_name][cage_name].append(host)
        return customers

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        extra_args = {}
        extra_args['dest'] = self._task.args.get('dest', None)
        dest = extra_args['dest']
        extra_args['identity_file'] = self._task.args.get('identity_file', None)
        extra_args['user'] = self._task.args.get('user', None)
        extra_args['bastion_user'] = self._task.args.get('bastion_user', None)
        extra_args['force'] = self._task.args.get('force', False)

        if not tmp:
            tmp = self._make_tmp_path()
        try:
            customers = self.build_customers(task_vars)
        except Exception as e:
            result['failed']=True
            result['msg']="In bastion_ssh_config plugin:build_customers "+type(e).__name__ + ": " + str(e)
            return result

        configs={}
        failed=False
        changed=False
        for customer_name in customers:
            for cage_name in customers[customer_name]:
                if customer_name == "None" or cage_name == "None":
                    continue
                try:
                    result, config = self.ssh_config(customers, customer_name, cage_name, tmp, task_vars, result, complex_args=extra_args)
                    temp_src=os.path.join(tmp, customer_name+"_"+cage_name)
                    config_dest=os.path.join(dest, customer_name, cage_name)
                    result = self.materialize_results(config_dest, config, temp_src, task_vars, result, extra_args)
                    failed |= result.get('failed', False)
                    changed |= result.get('changed', False)
                    configs[cage_name]=result
                except Exception as e:
                    result['failed']=True
                    result['msg']="In bastion_ssh_config plugin, E1: "+type(e).__name__ + ": " + str(e)
                    return result

        # self.cleanup(tmp)
        result['failed']=failed
        result['changed']=changed
        # result['configs']=configs
        result['msg']="Generated ssh configs"
        return result

    def ssh_config(self, customers, customer_name, cage_name, tmp, task_vars, result, complex_args=None):
        try:
            args = {}
            if complex_args:
                args.update(complex_args)

            if not 'dest' in args:
                raise ae("'dest' is a required argument.")
            if not 'identity_file' in args:
                raise ae("'identity_file' is a required argument.")

            dest = args.get('dest', None)
            identity_file = args.get('identity_file', None)
            default_user = args.get('user', 'ec2-user')
            bastion_user = args.get('bastion_user', args.get('user', 'ec2-user'))
            domain = task_vars['customer_domain']

            # Iterate though all hosts in the customer, cage pair
            bastion_entries=[]
            entries=[]
            for host in customers[customer_name][cage_name]:
                data = {}
                data.update(task_vars)
                data.update(task_vars['hostvars'][host])

                # TODO use nucleator facts instead
                private_ip = data['ec2_private_ip_address']
                user = data.get('ansible_ssh_user', default_user)
                instance_name = host
                bastion_suffix = instance_name.split(".")
                short_name=bastion_suffix.pop(0)
                bastion_suffix = "{0}.{1}".format(cage_name, domain)
                configfile=os.path.join(dest, customer_name, cage_name)

                if short_name == "bastion":
                    bastion_user = user
                    bastion_entries += ssh_config_bastion_entry(
                        "".join( (short_name, "-", cage_name) ),
                        instance_name,
                        instance_name,
                        bastion_user,
                        identity_file)
                else:
                    # host shortcut by FQDN (except bastion, which uses for-real external routing)
                    entries += ssh_config_entry(
                        "".join( (short_name, "-", cage_name) ),
                        instance_name,
                        private_ip,
                        user,
                        identity_file,
                        configfile,
                        bastion_user,
                        bastion_suffix)

                # host shortcut by "Group-Cage"
                entries += ssh_config_entry(
                    "".join( (short_name, "-", cage_name) ),
                    "".join( (short_name, "-", cage_name) ),
                    private_ip,
                    user,
                    identity_file,
                    configfile,
                    bastion_user,
                    bastion_suffix)

                # host shortcut by private_ip
                entries += ssh_config_entry(
                    "".join( (short_name, "-", cage_name) ),
                    private_ip,
                    private_ip,
                    user,
                    identity_file,
                    configfile,
                    bastion_user,
                    bastion_suffix)

            config = ssh_config_header()
            config += SEPARATOR
            config += "".join(bastion_entries)
            config += SEPARATOR
            config += "".join(entries)

        except Exception as e:
            result['failed']=True
            result['msg']=type(e).__name__ + ": " + str(e)
            return result, None

        return result, config

    def materialize_results(self, destination, resultant, tmp, task_vars, result, extra_args):
        # Expand any user home dir specification
        dest = self._remote_expand_user(destination)
        local_checksum = checksum_s(resultant)
        remote_checksum = self.get_checksum(dest, task_vars)
        if isinstance(remote_checksum, dict):
            # Error from remote_checksum is a dict.  Valid return is a str
            result.update(remote_checksum)
            return result

        diff = {}
        new_module_args = self._task.args.copy()
        # have to manually create the tmp dir
        cmd = self._connection._shell.mkdtemp(tmp, True, 0o700, None)
        mkdir_result = self._low_level_execute_command(cmd, sudoable=False)
        self._display.v("mkdir "+cmd)

        if (remote_checksum == '1') or (extra_args['force'] and local_checksum != remote_checksum):

            result['changed'] = True
            # if showing diffs, we need to get the remote value
            if self._play_context.diff:
                diff = self._get_diff_data(dest, resultant, task_vars, source_file=False)

            if not self._play_context.check_mode:  # do actual work through copy
                remote_path = self._connection._shell.join_path(tmp, 'source')
                xfered = self._transfer_data(remote_path, resultant)
                self._display.v("data xfer to "+remote_path)
                self._display.v("data xfer result "+xfered)

                # fix file permissions when the copy is done as a different user
                self._fixup_perms2((tmp, xfered))

                tmp_module_args = dict(
                    path = os.path.dirname(dest),
                    state = 'directory'
                )
                result.update(self._execute_module(module_name='file', module_args=tmp_module_args, delete_remote_tmp=False))
                self._display.vvv("data mkdir tmpdir "+os.path.dirname(dest))
                self._display.vvv("data mkdir result "+str(result))

                # run the copy module
                new_module_args.update(
                    dict(
                        src=xfered,
                        dest=dest,
                        # original_basename=os.path.basename(source),
                        follow=True,
                    )
                )
                del new_module_args['bastion_user']
                del new_module_args['identity_file']
                del new_module_args['user']
                result.update(self._execute_module(module_name='copy', module_args=new_module_args, task_vars=task_vars, tmp=tmp, delete_remote_tmp=False))

            if result.get('changed', False) and self._play_context.diff:
                result['diff'] = diff

        else:
            # when running the file module based on the template data, we do
            # not want the source filename (the name of the template) to be used,
            # since this would mess up links, so we clear the src param and tell
            # the module to follow links.  When doing that, we have to set
            # original_basename to the template just in case the dest is
            # a directory.
            del new_module_args['bastion_user']
            del new_module_args['identity_file']
            del new_module_args['user']
            new_module_args.update(
                dict(
                    src=None,
                    # original_basename=os.path.basename(source),
                    follow=True,
                ),
            )
            result.update(self._execute_module(module_name='file', module_args=new_module_args, task_vars=task_vars, tmp=tmp, delete_remote_tmp=False))
        return result


    def cleanup(self, tmp):
        '''
        because we loop on generating a distinct ssh config for each cage,
        using module calls for the "copy" and "file" modules for each one,
        the ssh_config code sets "delete_remote_tmp" to False, to retain
        the tmp dir used to pass material to those modules.

        when we're done we now need to clean that up
        '''

        if "tmp" in tmp and not C.DEFAULT_KEEP_REMOTE_FILES:
            self._remove_tmp_path(tmp)
            cleanup_cmd = conn.shell.remove(tmp, recurse=True)
            self.runner._low_level_exec_command(conn, cleanup_cmd, tmp, sudoable=False)

SEPARATOR = """#---------------------------------------------------------------------------------------------------------------------------------------------#

"""

# TODO -- at some point, turn StrictHostKeyChecking on

HEADER_FORMAT = """#---------------------------------------------------------------------------------------------------------------------------------------------#
# Nucleator SSH Config
#---------------------------------------------------------------------------------------------------------------------------------------------#
Host *
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
    TCPKeepAlive=yes
    ServerAliveInterval 15
    ServerAliveCountMax 16

"""

BASTION_FORMAT = """# {0}-public
Host {1}
        Hostname {2}
        User {3}
        IdentityFile {4}

"""

INSTANCE_FORMAT = """# {0}
Host {1}
        Hostname {2}
        User {3}
        IdentityFile {4}
        ProxyCommand ssh -F {5} {6}@bastion.{7} nc %h %p

"""

def ssh_config_header():
    """Creates a header block for the ssh config file"""

    return HEADER_FORMAT

def ssh_config_bastion_entry(entry_comment, short_name, hostname, bastion_user, identity):
    """Creates a single ssh config entry with bastion proxy command"""

    return BASTION_FORMAT.format(
            entry_comment,
            short_name,
            hostname,
            bastion_user,
            identity)

def ssh_config_entry(entry_comment, short_name, hostname, user, identity, configfile, bastion_user, suffix):
    """Creates a single ssh config entry with bastion proxy command"""

    return INSTANCE_FORMAT.format(
            entry_comment,
            short_name,
            hostname,
            user,
            identity,
            configfile,
            bastion_user,
            suffix)
