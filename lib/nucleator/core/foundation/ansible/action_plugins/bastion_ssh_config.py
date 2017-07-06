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
from ansible import utils
from ansible.inventory import Inventory
from ansible.inventory.host import Host
from ansible.inventory.group import Group
import ansible.constants as C

import os, json

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

    # def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        if not tmp:
            tmp = self._make_tmp_path()
        # with open('/tmp/bsc.log', 'w') as f:
        #     f.write("TV: "+str(task_vars))
        try:
            customers = self.build_customers(task_vars)
        except Exception as e:
            result['failed']=True
            result['msg']=type(e).__name__ + ": " + str(e)
            return result

        configs={}
        failed=False
        changed=False
        # comm_ok=True
        for customer_name in customers:
            for cage_name in customers[customer_name]:
                if customer_name == "None" or cage_name == "None":
                    continue
                try:
                    result, config = self.ssh_config(customers, customer_name, cage_name, tmp, task_vars, result)
                    config_dest=os.path.join(dest, customer_name, cage_name)
                    result = self.materialize_results(config_dest, config, result)
                    failed |= result.get('failed', False)
                    changed |= result.get('changed', False)
                    # comm_ok &= communicated_ok()
                    configs[cage_name]=result

                except Exception as e:
                    result['failed']=True
                    result['msg']=type(e).__name__ + ": " + str(e)
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

                bastion_suffix = "{0}.{1}".format(cage_name,data['hostvars']['localhost']['customer_domain'])
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
            return result

        return result, config
        # return self.materialize_results(config_dest, config, result)
        # return self.materialize_results(config_dest, config, conn, tmp, 'dontcare', module_args, task_vars=task_vars, complex_args=complex_args, **kwargs)

    def materialize_results(self, destination, resultant, tmp, task_vars, result):
        # Expand any user home dir specification
        dest = self._remote_expand_user(destination)

        directory_prepended = False
        if dest.endswith(os.sep):
            # Optimization.  trailing slash means we know it's a directory
            directory_prepended = True
            dest = self._connection._shell.join_path(dest, os.path.basename(source))
        else:
            # Find out if it's a directory
            dest_stat = self._execute_remote_stat(dest, task_vars, True, tmp=tmp)
            if dest_stat['exists'] and dest_stat['isdir']:
                dest = self._connection._shell.join_path(dest, os.path.basename(source))

        local_checksum = checksum_s(resultant)
        remote_checksum = self.get_checksum(dest, task_vars, not directory_prepended, source=source, tmp=tmp)
        if isinstance(remote_checksum, dict):
            # Error from remote_checksum is a dict.  Valid return is a str
            result.update(remote_checksum)
            return result

        diff = {}
        new_module_args = self._task.args.copy()

        if (remote_checksum == '1') or (force and local_checksum != remote_checksum):

            result['changed'] = True
            # if showing diffs, we need to get the remote value
            if self._play_context.diff:
                diff = self._get_diff_data(dest, resultant, task_vars, source_file=False)

            if not self._play_context.check_mode:  # do actual work through copy
                xfered = self._transfer_data(self._connection._shell.join_path(tmp, 'source'), resultant)

                # fix file permissions when the copy is done as a different user
                self._fixup_perms2((tmp, xfered))

                # run the copy module
                new_module_args.update(
                    dict(
                        src=xfered,
                        dest=dest,
                        original_basename=os.path.basename(source),
                        follow=True,
                        ),
                )
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
            new_module_args.update(
                dict(
                    src=None,
                    original_basename=os.path.basename(source),
                    follow=True,
                ),
            )
            result.update(self._execute_module(module_name='file', module_args=new_module_args, task_vars=task_vars, tmp=tmp, delete_remote_tmp=False))
        return result

    # def materialize_results(self, dest, resultant, conn, tmp, module_name, module_args, task_vars, complex_args=None, **kwargs):
    #     '''
    #     Place resultant in-memory output string text "resultant" at target destination dir "dest" in target file "resultant_basename".
    #     '''
    #     dest=os.path.abspath(os.path.expanduser(dest))
    #     (dest_path, dest_basename)=os.path.split(dest)
    #     # ensure dest directory exists
    #     vv ("ensuring ssh config target directory {0} exists".format(dest_path))
    #     file_module_args = dict(
    #         path=dest_path,
    #         state="directory"
    #     )
    #     if self._play_context.check_mode:        #self.runner.noop_on_check(task_vars):
    #         file_module_args['CHECKMODE'] = True
    #     file_module_args = utils.merge_module_args("", file_module_args)
    #     res = self._execute_module(conn, tmp, 'file', file_module_args, task_vars=task_vars, delete_remote_tmp=False)

    #     # compare resultant string with current contents of destination
    #     vv ("comparing checksums")
    #     local_checksum = utils.checksum_s(resultant)
    #     remote_checksum = self._remote_checksum(dest, task_vars)

    #     if local_checksum != remote_checksum:

    #         # template is different from the remote value
    #         vv ("checksums differ")

    #         # if showing diffs, we need to get the remote value
    #         dest_contents = ''

    #         if self._play_context.diff:
    #             # using persist_files to keep the temp directory around to avoid needing to grab another
    #             dest_result = self._execute_module(conn, tmp, 'slurp', "path=%s" % dest, inject=inject, persist_files=True)
    #             if 'content' in dest_result.result:
    #                 dest_contents = dest_result.result['content']
    #                 if dest_result.result['encoding'] == 'base64':
    #                     dest_contents = base64.b64decode(dest_contents)
    #                 else:
    #                     raise Exception("unknown encoding, failed: %s" % dest_result.result)

    #         self._display.vv ("transfering {0}, {1}, {2}, {3}".format(conn, tmp, 'source', resultant))
    #         # xfered = self.runner._transfer_str(conn, tmp, 'source', resultant)
    #         xfered = self._transfer_data(self._connection._shell.join_path(tmp, 'source'), resultant)
    #         self._display.vv ("transfer successful!!")

    #         # fix file permissions when the copy is done as a different user

    #         # ansible pre-1.9.4 uses "sudo" & "sudo_user" or "su" & "su_user"
    #         sudo_18=getattr(self.runner, "sudo", False)
    #         su_18=getattr(self.runner, "su", False)
    #         # ansible 1.9.4-1 uses "become" & "become_user"
    #         become_1941=getattr(self.runner,"become", False)

    #         if sudo_18 and self.runner.sudo_user != 'root' or su_18 and self.runner.su_user != 'root' or become_1941 and self.runner.become_user != 'root':
    #             self.runner._remote_chmod(conn, 'a+r', xfered, tmp)

    #         # run the copy module
    #         self._display.vv ("running copy module")
    #         new_module_args = dict(
    #            src=xfered,
    #            dest=dest,
    #            original_basename=dest_basename,
    #            follow=True,
    #         )
    #         module_args_tmp = utils.merge_module_args(module_args, new_module_args)
    #         res = self._execute_module(conn, tmp, 'copy', module_args_tmp, inject=inject, delete_remote_tmp=False, complex_args=None)
    #         if res.result.get('changed', False):
    #             res.diff = dict(before=dest_contents, after=resultant)
    #         return res

    #     else:
    #         self._display.vv ("checksums match, using file module to fix up file parameters")

    #         # when running the file module based on the template data, we do
    #         # not want the source filename (the name of the template) to be used,
    #         # since this would mess up links, so we clear the src param and tell
    #         # the module to follow links.  When doing that, we have to set
    #         # original_basename to the template just in case the dest is
    #         # a directory.
    #         new_module_args = dict(
    #             src=None,
    #             dest=dest,
    #             original_basename=dest_basename,
    #             follow=True,
    #         )
    #         # be sure to inject the check mode param into the module args and
    #         # rely on the file module to report its changed status
    #         if self.runner.noop_on_check(inject):
    #             new_module_args['CHECKMODE'] = True
    #         file_module_args = utils.merge_module_args(module_args, new_module_args)
    #         file_module_complex_args=complex_args
    #         for stripkey in  [ "identity_file", "user", "bastion_user" ]:
    #             if stripkey in file_module_complex_args:
    #                 del file_module_complex_args[stripkey] # not supported or needed by file module
    #         return self._execute_module(conn, tmp, 'file', file_module_args, inject=inject, delete_remote_tmp=False, complex_args=file_module_complex_args)

    def cleanup(self, tmp):
        pass
        '''
        because we loop on generating a distinct ssh config for each cage,
        using module calls for the "copy" and "file" modules for each one,
        the ssh_config code sets "delete_remote_tmp" to False, to retain
        the tmp dir used to pass material to those modules.

        when we're done we now need to clean that up
        '''

        # if "tmp" in tmp and not C.DEFAULT_KEEP_REMOTE_FILES:
        #     self._remove_tmp_path(tmp)
            # cleanup_cmd = conn.shell.remove(tmp, recurse=True)
            # self.runner._low_level_exec_command(conn, cleanup_cmd, tmp, sudoable=False)

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
