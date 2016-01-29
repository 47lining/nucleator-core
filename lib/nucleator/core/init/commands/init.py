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

from nucleator.cli.command import Command
from nucleator.cli import utils
from nucleator.cli import ansible
from nucleator.cli import properties

from distutils.version import StrictVersion

import os, subprocess

class Init(Command):
    
    name = "init"
    
    def parser_init(self, subparsers):
        """
        Initialize parsers for this command.
        """
        init_parser = subparsers.add_parser('init')

    def init(self, **kwargs):
        """
        This command initializes your nucleator configuration:
        
          - Initializes and populates a .nucleator configuration directory in user's home 
            directory with sample Customer, Account and Cage configs

          - Places initial manifest of versioned nucleator Cage and Stackset Modules with 
            repo sources in nucleator configuration directory

          - Populates an initial rolespec directory with Role definitions required for use 
            of nucleator modules

          - Validates nucleator pre-requisites (ansible, aws) and provides installation 
            instructions if missing 
        """

        self.check_prerequisites()

        cli=kwargs.get("cli", None)
        if cli is None:
            raise ValueError("INTERNAL ERROR: cli should have been set by upstream code, but is not specified")
        extra_vars={
            "verbosity": kwargs.get("verbosity", None),
            "nucleator_dynamic_hosts_src": properties.DYNAMIC_HOSTS_SRC,
            "nucleator_dynamic_hosts_dest": properties.DYNAMIC_HOSTS_PATH,
        }
        return cli.safe_playbook(
            self.get_command_playbook("init.yml"),
            is_static="Bootstrap",
            **extra_vars
        )

    def check_prerequisites(self):
        """Check that nucleator pre-requisites are in place"""

        # graffiti monkey
        utils.write("\nChecking graffiti monkey installation...\n")
        try:
            import graffiti_monkey
            from graffiti_monkey.core import GraffitiMonkey
            no_graffiti_monkey=False
        except ImportError:
            no_graffiti_monkey=True
            msg="Prerequisite graffiti_monkey not found.\nNucleator requires graffiti_monkey to run. " \
                "You can install it via:\n" \
                "\tpip install graffiti_monkey==0.7"
            utils.write_err(msg, False)
            utils.write_err("Missing pre-requisite, exiting")
            return

        # paramiko
        utils.write("\nChecking paramiko installation...\n")
        try:
            import paramiko
            no_paramiko=False
        except ImportError:
            no_paramiko=True
            msg="Prerequisite paramiko not found.\nNucleator requires paramiko to run. " \
                "You can install it via:\n" \
                "\tpip install paramiko"
            utils.write_err(msg, False)
            utils.write_err("Missing pre-requisite, exiting")
            return

        # pyyaml
        utils.write("\nChecking pyyaml installation...\n")
        try:
            import yaml
            no_yaml=False
        except ImportError:
            no_yaml=True
            msg="Prerequisite pyyaml not found.\nNucleator requires pyyaml to run. " \
                "You can install it via:\n" \
                "\tpip install pyyaml"
            utils.write_err(msg, False)
            utils.write_err("Missing pre-requisite, exiting")
            return

        # jinja2
        utils.write("\nChecking jinja2 installation...\n")
        try:
            import jinja2
            no_jinja2=False
        except ImportError:
            no_jinja2=True
            msg="Prerequisite jinja2 not found.\nNucleator requires jinja2 to run. " \
                "You can install it via:\n" \
                "\tpip install jinja2"
            utils.write_err(msg, False)
            utils.write_err("Missing pre-requisite, exiting")
            return

        # ansible
        utils.write("\nChecking ansible Installation\n")
        try:
            utils.write(subprocess.check_output(["ansible-playbook", "--version"]))
            no_ansible=False
        except OSError:
            no_ansible=True
        if no_ansible:
            msg="Prerequisite ansible not found.\nNucleator requires ansible to run. " \
                "You can install it with all 47Lining pull requests via:\n" \
                "\tgit clone --recursive --depth 1 -b nucleator_distribution https://github.com/47lining/ansible.git\n" \
                "\tcd ansible; sudo python setup.py install"
            utils.write_err(msg, False)

        # aws CLI
        utils.write("\nChecking aws CLI installation...\n")
        try:
            utils.write(subprocess.check_output(["aws", "--version"]))
            no_aws=False
        except OSError:
            no_aws=True
        if no_aws:
            msg="Prerequisite aws not found.\nNucleator requires aws to run. " \
                "You can install it via:\n" \
                "\tpip install awscli"
            utils.write_err(msg, False)
        
        # httplib2
        utils.write("\nChecking httplib2 installation...\n")
        try:
            import httplib2
            no_httplib2=False
        except ImportError:
            no_httplib2=True
            msg="Prerequisite httplib2 not found.\nNucleator requires httplib2 to run. " \
                "You can install it via:\n" \
                "\tpip install httplib2"
            utils.write_err(msg, False)
        
        # boto
        utils.write("\nChecking boto installation...\n")
        try:
            import boto
            utils.write(boto.Version + "\n")
            no_boto=False
            if not StrictVersion(boto.Version) >= StrictVersion('2.38.0'):
                msg="Prerequisite boto not up to date.\nNucleator requires boto version 2.38.0 or greater to run. " \
                "You can install it via:\n" \
                "\tpip install boto"
                utils.write_err(msg, False)
                no_boto = True
        except ImportError:
            no_boto=True
            msg="Prerequisite boto not found.\nNucleator requires boto to run. " \
                "You can install it via:\n" \
                "\tpip install boto"
            utils.write_err(msg, False)

        if no_ansible or no_aws or no_boto or no_paramiko or no_yaml or no_jinja2 or no_httplib2:
            utils.write_err("Missing pre-requisite, exiting")

# Create the singleton for auto-discovery
command = Init()

