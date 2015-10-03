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

from nucleator.cli.cli import Cli
from nucleator.cli import unbuffered_subprocess as usp
from properties import *
from utils import *

import os, shlex, pipes, uuid, time, subprocess, re

import yaml, json, copy

aws_environment_with_rolenames={}

class CliWithAnsibleLauncher(Cli):

    def ansible_path(self, type):
        return ":".join( [os.path.join(p, "ansible", type) for p in self.command_paths] )

    def ansible_path_list(self, subpath, isdir=False):

        return [ref.get_command_ansible_path(subpath, isdir)
                for name,ref in self.commands.iteritems()
                if ref.get_command_ansible_path(subpath, isdir) is not None]

    def safe_playbook(self, playbook_absolute_path, inventory_manager_rolename=None, is_static=False, **extra_vars):
        if not os.path.isfile(playbook_absolute_path):
            raise ValueError("INTERNAL ERROR. No playbook exists at specified path, possible flawed implementation of contributed command.\nPlaybook = {0}".format(playbook_absolute_path))

        try:
            results=self.launch_playbook(playbook_absolute_path, inventory_manager_rolename, is_static, **extra_vars)
        except Exception, e:
            write_err("Caught exception during execution of playbook {0}: {1}\nExiting...".format(playbook_absolute_path, e))
        return results
    
    def launch_playbook(self, 
        playbook_absolute_path,
        inventory_manager_rolename = None,
        is_static=False,
        **EXTRA_VARS):
        """ Launch ansible playbook at specified path """
        
        global aws_environment_with_rolenames

        EXTRA_VARS["aws_environment_with_rolenames"] = aws_environment_with_rolenames

        if not inventory_manager_rolename is None:

            aws_environment_with_rolenames = json.loads(aws_environment_with_rolenames)
                
            os.environ["AWS_ACCESS_KEY_ID"] = aws_environment_with_rolenames[inventory_manager_rolename]["AWS_ACCESS_KEY_ID"]
            os.environ["AWS_SECRET_ACCESS_KEY"] = aws_environment_with_rolenames[inventory_manager_rolename]["AWS_SECRET_ACCESS_KEY"]
            os.environ["AWS_SECURITY_TOKEN"] = aws_environment_with_rolenames[inventory_manager_rolename]["AWS_SECURITY_TOKEN"]
        
        cage_name=EXTRA_VARS['cage_name'] if 'cage_name' in EXTRA_VARS else "bootstrap"
        customer_name=EXTRA_VARS['customer_name'] if 'customer_name' in EXTRA_VARS else ""
        limit_stackset=EXTRA_VARS.pop("limit_stackset", None)
        limit_stackset_instance=EXTRA_VARS.pop("limit_stackset_instance", None)
        list_hosts=EXTRA_VARS.pop("list_hosts", None)

        is_bootstrap=True if is_static == "Bootstrap" else False
        HOSTS=BOOTSTRAP_HOSTS_PATH if is_bootstrap else STATIC_HOSTS_PATH if is_static else DYNAMIC_HOSTS_PATH

        limit_group = ""
        if customer_name != "":
            limit_group += "tag_NucleatorCustomer_{0}".format(customer_name)
        if cage_name is not None:
            limit_group += ":&tag_NucleatorCage_{0}".format(cage_name)
        if limit_stackset is not None:
            limit_group += ":&tag_NucleatorStackset_{0}".format(limit_stackset)
            if limit_stackset_instance is not None:
                limit_group += ":&tag_NucleatorStacksetInstance_{0}".format(limit_stackset_instance)

        limit_group="" if is_static else limit_group

        REQUIRED_OPTS=[
            "-c", "ssh",
            "-i", HOSTS,
        ]
        EXTRA_OPTS=[
            #        "--list-hosts",
            #        "--list-tasks",
            #        "--syntax-check",
            #        "--ask-sudo-pass",
        ]

        if limit_group != "":
            EXTRA_OPTS.extend( [ "--limit", limit_group, ] )
      
        if list_hosts and not is_static:
            EXTRA_OPTS.extend( [ "--list-hosts" ] )
      
        if EXTRA_VARS['verbosity'] > 0:
            EXTRA_OPTS.extend(
                [
                    "--verbose",
                    "-" + ("v" * EXTRA_VARS['verbosity']),
                ]
            )
            
        ANSIBLE_SSH_ARGS=[
            "-F", os.path.join(NUCLEATOR_CONFIG_DIR, "ssh-config", customer_name, cage_name),
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=60",
            "-o", "ControlMaster=auto",
            "-o", "ControlPersist=15m",
            "-o", "ConnectionAttempts=3",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=20",
        ]
    
        # obtain temporary credentials in the target account using the source account
        # (sets and exports AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_SECURITY_TOKEN)
    
        os.environ["PYTHONUNBUFFERED"]="1"
    
        ANSIBLE_ENVIRONMENT={
            "PYTHONUNBUFFERED": "1",
            "ANSIBLE_COW_SELECTION": "bethany-sheep",
            "EC2_INI_PATH": EC2_INI_PATH,
            "ANSIBLE_LOCATION": ANSIBLE_LOCATION,
            "ANSIBLE_CONFIG": ANSIBLE_CONFIG,
            "ANSIBLE_SSH_ARGS": "{0}".format(" ".join(ANSIBLE_SSH_ARGS)),
            "PATH": get_clean("PATH"),
            "PYTHONPATH": get_clean("PYTHONPATH"),
            "HOME": get_clean("HOME"),
            "ANSIBLE_LIBRARY": self.ansible_path("library"),
            "ANSIBLE_ROLES_PATH": self.ansible_path("roles"),
            "ANSIBLE_ACTION_PLUGINS": self.ansible_path("action_plugins"),
            "ANSIBLE_CACHE_PLUGINS": self.ansible_path("cache_plugins"),
            "ANSIBLE_CONNECTION_PLUGINS": self.ansible_path("connection_plugins"),
            "ANSIBLE_LOOKUP_PLUGINS": self.ansible_path("lookup_plugins"),
            "ANSIBLE_VARS_PLUGINS": self.ansible_path("vars_plugins"),
            "ANSIBLE_FILTER_PLUGINS": self.ansible_path("filter_plugins"),
            "AWS_ACCESS_KEY_ID": get_clean("AWS_ACCESS_KEY_ID"),
            "AWS_SECRET_ACCESS_KEY": get_clean("AWS_SECRET_ACCESS_KEY"),
            "AWS_SECURITY_TOKEN": get_clean("AWS_SECURITY_TOKEN")
        }

        #print "TESTING: ", ANSIBLE_ENVIRONMENT
        #print "TEST: ", os.environ.get("PYTHONUNBUFFERED")

        # filter empty values from environment
        ANSIBLE_ENVIRONMENT=dict((k,v) for (k,v) in ANSIBLE_ENVIRONMENT.iteritems() if v is not None)
        
        ANSIBLE_MODS=[]
    
        ANSIBLE_COMMAND = ["ansible-playbook"]
        ANSIBLE_COMMAND.extend(REQUIRED_OPTS)
        ANSIBLE_COMMAND.extend(EXTRA_OPTS)
        ANSIBLE_COMMAND.extend([playbook_absolute_path])

        SANITIZED_COMMAND = copy.copy(ANSIBLE_COMMAND)

        SANITIZED_COMMAND.extend(["--extra-vars", '{0}'.format(
            " ".join("%s=%s" % (key,pipes.quote(str(val)))
                     for (key,val) in self.sanitize_dict(EXTRA_VARS).iteritems()))])
        SANITIZED_COMMAND.extend(ANSIBLE_MODS)
    
        ANSIBLE_COMMAND.extend(["--extra-vars", '{0}'.format(
            " ".join("%s=%s" % (key,pipes.quote(str(val)))
                     for (key,val) in EXTRA_VARS.iteritems()))])
        ANSIBLE_COMMAND.extend(ANSIBLE_MODS)

        # say what we're going to do
        sanitized_env = self.sanitize_dict(ANSIBLE_ENVIRONMENT)
        ENV_STRING=" ".join("%s=%s" % (key,pipes.quote(str(val))) for (key,val) in sanitized_env.iteritems())
        CMD_STRING=" ".join(pipes.quote(s) for s in ANSIBLE_COMMAND)

        SANITIZED_STRING = " ".join(pipes.quote(s) for s in SANITIZED_COMMAND)
        write("{0} {1}\n".format(ENV_STRING, SANITIZED_STRING))
    
    
        TEE_FILE_UUID=uuid.uuid4()
        TEE_FILE=os.path.join(os.path.sep, "tmp", "-".join([str(TEE_FILE_UUID), "output.txt"]))
    
        START=time.time()
        
        # then do it
        playbook = usp.Popen(
            ANSIBLE_COMMAND,
            shell=False,
            env=ANSIBLE_ENVIRONMENT,
            stdout=usp.PIPE,
            stderr=usp.PIPE,
        )
        playbook_out, playbook_err = playbook.communicate()
        rc = playbook.returncode

        fatal=subprocess.Popen(
            ["grep", "-E", "FATAL:|fatal:|Fatal:|ERROR:"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        fatal_out, fatal_err = fatal.communicate(playbook_out)
        FOUND_FATAL=True if fatal.returncode==0 else False
    
        END=time.time()
        ELAPSED=END-START
    
        write("\nScript Execution Time: {0:.2f} Seconds\n".format(ELAPSED))
    
        if rc !=0:
            write_err("Non-zero return code from playbook.\n\ncaptured stderr:\n{0}\n\n exiting with return code 1...".format(playbook_err))
        elif FOUND_FATAL:
            write_err("Found 'FATAL' or 'ERROR' in output, exiting with return code 1...")
        else:
            write("SUCCESS - successfully ran playbook {0}\n\n".format(os.path.basename(playbook_absolute_path)))
    
        result=dict(stdout=playbook_out, stderr=playbook_err, rc=rc, fatal=FOUND_FATAL)
        return result

    def sanitize_dict(self, input_dict):
        output_dict = input_dict.copy()
        for key, value in output_dict.items():
            if key == "aws_environment_with_rolenames":
                if type(value) in (str, unicode):
                    value = json.loads(value)
            if key.startswith("AWS_"):
                value = "(hidden)"
            elif type(value) == dict:
                value = self.sanitize_dict(value)
            output_dict[key] = value
        return output_dict

    def obtain_credentials(self, commands=None, account=None, cage=None, customer=None, verbosity=None):
        write_info("Obtaining Temporary Credentials")
        # provide what we have, the playbook will generate any missing facts
        extra_vars={}
        if account is not None:
            extra_vars["account_name"]=account
        if cage is not None:
            extra_vars["cage_name"]=cage
        if customer is not None:
            extra_vars["customer_name"]=customer

        extra_vars["verbosity"]=verbosity

        global aws_environment_with_rolenames
        #aws_environment_with_rolenames = {}

        cli=self

        role_list = []
        
        for command in commands:
            
            #Runs through the list of all role specification files if the command matches the commandname specified
            for command_name, command_ref in [
                    (n, r) for (n, r) in cli.commands.iteritems()
                    if r.get_command_ansible_path("role_specification.yml") and (n == command)
            ]:
                
                file=command_ref.get_command_ansible_path("role_specification.yml")

                stream = open(file, 'r')
                roles = yaml.load(stream)
            
                #Runs for each role in the role specifiation file
                for roles in roles['role_specification']:

                    rolename = roles['role_name']
                    
                    #Makes sure the role has a trust policy
                    if roles['trust_policy'] is None:
                        print "No trust policy for role: ", rolename
                        continue
                    trust_policy_statement = roles['trust_policy']['Statement']
                    
                    #Makes sure the role has an AWS trust policy
                    for statement in trust_policy_statement:
                        try:
                            trust_policy_principal = statement['Principal']
                            
                            trust_policy_aws =  trust_policy_principal['AWS']
                            
                            role_list.append(rolename)

                        except Exception, e:
                            print "No AWS policy in statement for role: ", rolename

        #Sends the target and source role name to the playbook for every aws trust policy
        for item in role_list:

            print "Getting credentials for role: ", item
             
            extra_vars["rolename"]=item

            aws_environment_with_rolenames[item] = {}
             
            playbook=self.safe_playbook(
                self.get_nucleator_command("foundation").get_command_playbook("nucleator_credentials.yml"),
                is_static=True,
                **extra_vars
            )
            
            #filter=subprocess.Popen(
            #    ["grep", "-A", "1", "^NUCLEATOR_TEMPORARY_CREDENTIALS$"],
            #    stdin=subprocess.PIPE,
            #    stdout=subprocess.PIPE,
            #    stderr=subprocess.PIPE
            #)
            #filter_out, filter_err = filter.communicate(playbook['stdout'])
            #found=True if filter.returncode==0 else False
        
            #if not found:
            #    write_err("Unable to find temporary credentials, Exiting...")
        
            # HMMMmmmmm.  We only get stdout from the playbook, and need to rip out env variables to set from that.
            # What's the best way?  Seems like reverting to shell behavior isn't it.  Shouldn't we be 
            # parsing, splitting, then using os.environ[]
        
            #assignments=shlex.split(filter_out.split(os.linesep)[1])

            with open("/tmp/creds.conf", "r") as content_file:
                content = content_file.read()
            assignments = shlex.split(content)
            
            p = re.compile('([^=]+)=(.*)')
            for assignment in assignments:
                sides=p.match(assignment)
                if sides is None:
                    write_err('Unknown assignment: '+assignment)
                else:
                    key=sides.group(1)
                    value=sides.group(2)
                    aws_environment_with_rolenames[item][key]=value
                    #os.environ[key]=value
                write_info('Temporary Credentials: {0} = {1}'.format(key, value))
        
        aws_environment_with_rolenames = json.dumps(aws_environment_with_rolenames)

        os.remove("/tmp/creds.conf")

        return
