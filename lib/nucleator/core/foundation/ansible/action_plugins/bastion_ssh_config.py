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
try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

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

    # def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        try:
            # determine hosts in each cage for each customer
            customers={}
            for host in self.runner.host_set:
                data = {}
                data.update(inject)
                data.update(inject['hostvars'][host])

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

        except Exception as e:
            result['failed']=True
            result['msg']=type(e).__name__ + ": " + str(e)
            return result

        configs={}
        failed=False
        changed=False
        comm_ok=True
        for customer_name in customers:
            for cage_name in customers[customer_name]:
                if customer_name == "None" or cage_name == "None":
                    continue
                try:
                    return_data=self.ssh_config(customers, customer_name, cage_name, conn, tmp, module_name, module_args, inject, complex_args, **kwargs)
                    failed |= return_data.result.get('failed', False)
                    changed |= return_data.result.get('changed', False)
                    comm_ok &= return_data.communicated_ok()
                    configs[cage_name]=return_data.result

                except Exception as e:
                    result['failed']=True
                    result['msg']=type(e).__name__ + ": " + str(e)
                    return result

        self.cleanup(conn, tmp)
        result['failed']=failed
        result['changed']=changed
        result['configs']=configs
        result['msg']="Generated ssh configs"
        return result

    def ssh_config(self, customers, customer_name, cage_name, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        try:
            args = {}
            if complex_args:
                args.update(complex_args)
            args.update(parse_kv(module_args))

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
                data.update(inject)
                data.update(inject['hostvars'][host])

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

        config_dest=os.path.join(dest, customer_name, cage_name)
        return self.materialize_results(config_dest, config, conn, tmp, 'dontcare', module_args, inject=inject, complex_args=complex_args, **kwargs)

    def materialize_results(self, dest, resultant, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
        '''
        Place resultant in-memory output string text "resultant" at target destination dir "dest" in target file "resultant_basename".
        '''
        dest=os.path.abspath(os.path.expanduser(dest))
        (dest_path, dest_basename)=os.path.split(dest)
        # ensure dest directory exists
        vv ("ensuring ssh config target directory {0} exists".format(dest_path))
        file_module_args = dict(
            path=dest_path,
            state="directory",
        )
        if self.runner.noop_on_check(inject):
            file_module_args['CHECKMODE'] = True
        file_module_args = utils.merge_module_args("", file_module_args)
        res = self.runner._execute_module(conn, tmp, 'file', file_module_args, inject=inject, delete_remote_tmp=False)

        # compare resultant string with current contents of destination
        vv ("comparing checksums")
        local_checksum = utils.checksum_s(resultant)
        remote_checksum = self.runner._remote_checksum(conn, tmp, dest, inject)

        if local_checksum != remote_checksum:

            # template is different from the remote value
            vv ("checksums differ")

            # if showing diffs, we need to get the remote value
            dest_contents = ''

            if self.runner.diff:
                # using persist_files to keep the temp directory around to avoid needing to grab another
                dest_result = self.runner._execute_module(conn, tmp, 'slurp', "path=%s" % dest, inject=inject, persist_files=True)
                if 'content' in dest_result.result:
                    dest_contents = dest_result.result['content']
                    if dest_result.result['encoding'] == 'base64':
                        dest_contents = base64.b64decode(dest_contents)
                    else:
                        raise Exception("unknown encoding, failed: %s" % dest_result.result)

            display.vv ("transfering {0}, {1}, {2}, {3}".format(conn, tmp, 'source', resultant))
            xfered = self.runner._transfer_str(conn, tmp, 'source', resultant)
            display.vv ("transfer successful!!")

            # fix file permissions when the copy is done as a different user

            # ansible pre-1.9.4 uses "sudo" & "sudo_user" or "su" & "su_user"
            sudo_18=getattr(self.runner, "sudo", False)
            su_18=getattr(self.runner, "su", False)
            # ansible 1.9.4-1 uses "become" & "become_user"
            become_1941=getattr(self.runner,"become", False)

            if sudo_18 and self.runner.sudo_user != 'root' or su_18 and self.runner.su_user != 'root' or become_1941 and self.runner.become_user != 'root':
                self.runner._remote_chmod(conn, 'a+r', xfered, tmp)

            # run the copy module
            display.vv ("running copy module")
            new_module_args = dict(
               src=xfered,
               dest=dest,
               original_basename=dest_basename,
               follow=True,
            )
            module_args_tmp = utils.merge_module_args(module_args, new_module_args)
            res = self.runner._execute_module(conn, tmp, 'copy', module_args_tmp, inject=inject, delete_remote_tmp=False, complex_args=None)
            if res.result.get('changed', False):
                res.diff = dict(before=dest_contents, after=resultant)
            return res

        else:
            display.vv ("checksums match, using file module to fix up file parameters")

            # when running the file module based on the template data, we do
            # not want the source filename (the name of the template) to be used,
            # since this would mess up links, so we clear the src param and tell
            # the module to follow links.  When doing that, we have to set
            # original_basename to the template just in case the dest is
            # a directory.
            new_module_args = dict(
                src=None,
                dest=dest,
                original_basename=dest_basename,
                follow=True,
            )
            # be sure to inject the check mode param into the module args and
            # rely on the file module to report its changed status
            if self.runner.noop_on_check(inject):
                new_module_args['CHECKMODE'] = True
            file_module_args = utils.merge_module_args(module_args, new_module_args)
            file_module_complex_args=complex_args
            for stripkey in  [ "identity_file", "user", "bastion_user" ]:
                if stripkey in file_module_complex_args:
                    del file_module_complex_args[stripkey] # not supported or needed by file module
            return self.runner._execute_module(conn, tmp, 'file', file_module_args, inject=inject, delete_remote_tmp=False, complex_args=file_module_complex_args)

    def cleanup(self, conn, tmp):
        '''
        because we loop on generating a distinct ssh config for each cage,
        using module calls for the "copy" and "file" modules for each one,
        the ssh_config code sets "delete_remote_tmp" to False, to retain
        the tmp dir used to pass material to those modules.

        when we're done we now need to clean that up
        '''

        if "tmp" in tmp and not C.DEFAULT_KEEP_REMOTE_FILES:
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
