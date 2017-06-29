from __future__ import print_function
from nucleator.cli.command import Command
from nucleator.cli import properties
from nucleator.cli import ansible
from nucleator.cli.utils import ValidateAccountAction
from nucleator.cli.utils import ValidateCustomerAction

import os, subprocess
import json

class Account(Command):

    name = "account"

    def parser_init(self, subparsers):
        """
        Initialize parsers for this command.
        """

        # add parser for account command
        account_parser = subparsers.add_parser('account')
        account_subparsers=account_parser.add_subparsers(dest="subcommand")

        # setup subcommand
        setup=account_subparsers.add_parser('setup')
        setup.add_argument("--account", required=True, action=ValidateAccountAction, help="Friendly name of AWS Account from nucleator config")
        setup.add_argument("--customer", required=True, action=ValidateCustomerAction, help="Name of customer from nucleator config")

        # rolespec subcommand
        rolespec=account_subparsers.add_parser('rolespec')
        rolespec_subparsers=rolespec.add_subparsers(dest="subsubcommand")

        # list, provision and validate subsubcommands
        #
        ## list
        rolespec_list=rolespec_subparsers.add_parser('list')
        rolespec_list.add_argument("--rolename", required=False, help="Name of the role to be listed")
        rolespec_list.add_argument("--commandname", required=False, help="Name of the command to be listed")
        #
        ## provision
        rolespec_provision=rolespec_subparsers.add_parser('provision')
        rolespec_provision.add_argument("--rolename", required=False, help="Name of the role to be provisioned")
        rolespec_provision.add_argument("--commandname", required=False, help="Name of the command to be provisioned")
        rolespec_provision.add_argument("--account", required=True, action=ValidateAccountAction, help="Friendly name of AWS Account from nucleator config")
        rolespec_provision.add_argument("--customer", required=True, action=ValidateCustomerAction, help="Name of customer from nucleator config")

        #
        ## validate
        rolespec_validate=rolespec_subparsers.add_parser('validate')
        rolespec_validate.add_argument("--rolename", required=False, help="Name of the role to be validated")
        rolespec_validate.add_argument("--commandname", required=False, help="Name of the command to be validated")
        rolespec_validate.add_argument("--account", required=False, action=ValidateAccountAction, help="Friendly name of AWS Account from nucleator config")
        rolespec_validate.add_argument("--customer", required=True, action=ValidateCustomerAction, help="Name of customer from nucleator config")

    def setup(self, **kwargs):
        """
        The account setup command prepares a new Account for creation of Cages specified
        in the customer configuration.  It creates a hosted zone for each Cage in the Account,
        creates an S3 bucket for CloudFormation template storage used by all Nucleator
        modules within the Account and sets up the Account to conform with Nucleator operations
        best practices.
        """
        cli=Command.get_cli(kwargs)
        account = kwargs.get("account", None)
        customer = kwargs.get("customer", None)
        if account is None or customer is None:
            raise ValueError("account and customer must be specified")

        command_list = []
        command_list.append("account")

        cli.obtain_credentials(commands=command_list, account=account, customer=customer, verbosity=kwargs.get("verbosity", None), debug_credentials=kwargs.get("debug_credentials", None))

        extra_vars={
            "account_name": account,
            "customer_name": customer,
            "verbosity": kwargs.get("verbosity", None),
            "debug_credentials": kwargs.get("debug_credentials", None),
        }

        return cli.safe_playbook(
            self.get_command_playbook("account_setup.yml"),
            is_static=True, # do not use dynamic inventory script, credentials may not be available
            **extra_vars
        )

    def rolespec_list(self, **kwargs):
        """
        This command lists the names and descriptions of rolespecs currently available
        within Nucleator config (i.e., rolespecs for core plus all contrib installed
        modules)

        Implements the account rolespec list subsubcommand
        """

        import yaml

        print ("In command: account rolespec list")
        roleName = kwargs.get("rolename", None)

        command = kwargs.get("commandname", None)

        cli=Command.get_cli(kwargs)

        roleFound = False

        try:
            if not command is None:
                cli.get_nucleator_command(command)
        except Exception as e:
            print ("No command with that name. Run \"nucleator --help\" to see a list of available commands")
            return

        #Runs through the list of all role specification files if the command matches the commandname specified
        for command_name, command_ref in [
                (n, r) for (n, r) in cli.commands.items()
                if r.get_command_ansible_path("role_specification.yml") and (n == command or command is None)
        ]:

            file=command_ref.get_command_ansible_path("role_specification.yml")

            stream = open(file, 'r')
            roles = yaml.load(stream)

            #Runs if no rolename parameter is specified
            if roleName == None:
                #Prints the list of all roles
                for roles in roles['role_specification']:
                    print ("Role Name: ", roles['role_name'])
            else:
                #Prints the complete details of every role if "all" is specified
                if roleName == "all":
                    for roles in roles['role_specification']:
                        print ("Role Name: ", roles['role_name'])
                        print ("Trust Policy: ", json.dumps(roles['trust_policy'], indent=2, sort_keys=True))
                        print ("Access Policies: ", json.dumps(roles['access_policies'], indent=2, sort_keys=True))
                else:
                    #Prints the complete details of the role specified
                    for roles in roles['role_specification']:
                        if roles['role_name'] == roleName:
                            print ("Role Name: ", roles['role_name'])
                            print ("Trust Policy: ", json.dumps(roles['trust_policy'], indent=2, sort_keys=True))
                            print ("Access Policies: ", json.dumps(roles['access_policies'], indent=2, sort_keys=True))
                            roleFound = True
                if not roleFound:
                    print ("No roles with that name. Remove rolename parameter to see list of role names")

    def rolespec_provision(self, **kwargs):
        """
        This command adds IAM Roles and/or Instance Profiles within the AWS Account
        consistent with the specified rolespecs available in Nucleator config. Specify
        a single rolespec to provision, or provision all rolespecs.
        """

        import yaml

        print ("In command: account rolespec provision")

        cli=Command.get_cli(kwargs)

        playbooks=cli.ansible_path_list("role_provision.yml")

        roleFound = False
        firstRun = True

        command = kwargs.get("commandname", None)

        try:
            if not command is None:
                cli.get_nucleator_command(command)
        except Exception as e:
            print ("No command with that name. Run \"nucleator --help\" to see a list of available commands")
            return

        #Makes the first command builder so that Nucleator Agent is the first role provisioned
        if command is None:
            firstCommand = 'account'
        else:
            firstCommand = None

        #Runes through the complete list of role specification files
        role_playbook=self.get_command_playbook("role_provision.yml")
        for command_name, command_ref in [
                (n, r) for (n, r) in cli.commands.items()
                if r.get_command_ansible_path("role_specification.yml") and (n == command or command is None)
        ]:

            #Makes the first command builder so that Nucleator Agent is the first role provisioned
            if not firstCommand is None:
                if firstRun:
                    for (n, r) in cli.commands.items():
                        if n == firstCommand:
                            temp_command_name = command_name
                            temp_command_ref = command_ref
                            command_name = n
                            command_ref = r
                            firstRun = False
                else:
                    #Replaces the actual occurrence of builder with what was originially the first command to be run
                    if command_name == firstCommand:
                        command_name = temp_command_name
                        command_ref = temp_command_ref

            role_specification=command_ref.get_command_ansible_path("role_specification.yml")
            print ("using role_specification: ", role_specification)

            stream = open(role_specification, 'r')
            roles = yaml.load(stream)

            rolename = kwargs.get("rolename", None)

            #Runs if no role name is specified
            if rolename == None:
                rolename_list = []

                #Gets a list of all roles in that command and sends them to the playbook
                for roles in roles['role_specification']:
                    rolename_list.append(roles['role_name'])

                rolename_list = list(set(rolename_list))
                extra_vars={
                    "aws_role_names": json.dumps(rolename_list),
                    "role_specification_varsfile": role_specification,
                    "customer_name": kwargs.get("customer", None),
                    "account_name": kwargs.get("account", None),
                    "verbosity": kwargs.get("verbosity", None),
                    "debug_credentials": kwargs.get("debug_credentials", None),
                }
                print ("Role names sent to playbook are: ", rolename_list)
                cli.safe_playbook(
                    role_playbook,
                    is_static=True, # do not use dynamic inventory script, credentials may not be available
                    **extra_vars
                )
                roleFound = True
            else:
                #Sends the role specified to the playbook
                for roles in roles['role_specification']:
                    if roles['role_name'] == rolename:
                        print ("Role Name sent to playbook is: ", rolename)
                        extra_vars={
                            "role_names": rolename,
                            "role_specification_varsfile": role_specification,
                            "customer_name": kwargs.get("customer", None),
                            "account_name": kwargs.get("account", None),
                            "verbosity": kwargs.get("verbosity", None),
                            "debug_credentials": kwargs.get("debug_credentials", None),
                        }
                        cli.safe_playbook(
                            role_playbook,
                            is_static=True, # do not use dynamic inventory script, credentials may not be available
                            **extra_vars
                        )
                        roleFound = True
                        return
        if not roleFound:
            print ("No roles with that name in that command. Run list command to see list of role names or use no rolename parameter to provision all roles")

    def rolespec_validate(self, **kwargs):
        """
        Validates correct cross-account Role setup by attempting to assume one or more
        specified rolespec(s) in target account.
        """

        import yaml

        print ("In command: account rolespec validate")

        cli=Command.get_cli(kwargs)

        role_playbook=self.get_command_playbook("validate_credentials.yml")

        roleFound = False
        roleSucceeded = False

        customer = ""

        command = kwargs.get("commandname", None)

        try:
            if not command is None:
                cli.get_nucleator_command(command)
        except Exception as e:
            print ("No command with that name. Run \"nucleator --help\" to see a list of available commands")
            return

        try:
            #Gets the customer file for the customer specified
            customer_file = os.path.join(properties.contrib_path(), "siteconfig", "ansible", "roles", "siteconfig", "vars",
                ".".join([kwargs.get("customer", None),'yml']))

            stream = open(customer_file, 'r')
            customer = yaml.load(stream)
        except (Exception, IOError):
            print (kwargs.get("customer", None) + ".yml file could not be found")
            return

        #Gets the list of accounts for a given customer
        for account_name in customer["aws_accounts"]:

            #if an account is specified, only runs if the account matches the account specified
            if not kwargs.get("account", None) is None:
                if not account_name == kwargs.get("account", None):
                    continue

            #Runs through the list of all role specification files if the command matches the commandname specified
            for command_name, command_ref in [
                    (n, r) for (n, r) in cli.commands.items()
                    if r.get_command_ansible_path("role_specification.yml") and (n == command or command is None)
            ]:

                file=command_ref.get_command_ansible_path("role_specification.yml")

                stream = open(file, 'r')
                roles = yaml.load(stream)

                rolename = kwargs.get("rolename", None)

                #Runs if no role name is specified
                if rolename == None:

                    roleFound = True

                    #Runs for each role in the role specifiation file
                    for roles in roles['role_specification']:

                        rolename = roles['role_name']

                        roleSucceeded = False

                        print ("Role Name sent to playbook is: ", rolename)

                        aws_list = []

                        #Makes sure the role has a trust policy
                        if roles['trust_policy'] is None:
                            print ("No trust policy for role: ", rolename)
                            continue
                        trust_policy_statement = roles['trust_policy']['Statement']

                        #Makes sure the role has an AWS trust policy
                        for statement in trust_policy_statement:
                            try:
                                trust_policy_principal = statement['Principal']

                                trust_policy_aws =  trust_policy_principal['AWS']

                                #Adds the aws trust policy to the list in case there are multiple trusted relationships
                                for aws in trust_policy_aws:
                                    if len(aws) == 1:
                                        aws_list.append(trust_policy_aws)
                                        break

                                    aws_list.append(aws)

                            except Exception as e:
                                print ("No AWS policy in trust policy for role: ", rolename)

                            #Sends the target and source role name to the playbook for every aws trust policy
                            for item in aws_list:
                                trust_policy_role_name = item[item.index('/')+1:]

                                trust_policy_type = item[item.index('/')-4:item.index('/')]

                                if trust_policy_type == "role":

                                    extra_vars={
                                        "target_role_name": rolename,
                                        "source_role_name": trust_policy_role_name,
                                        "customer_name": kwargs.get("customer", None),
                                        "account_name": account_name,
                                        "verbosity": kwargs.get("verbosity", None),
                                        "debug_credentials": kwargs.get("debug_credentials", None),
                                    }
                                    cli.safe_playbook(
                                        role_playbook,
                                        is_static=True, # do not use dynamic inventory script, credentials may not be available
                                        **extra_vars
                                    )

                                    roleSucceeded = True

                                    break
                            if roleSucceeded:
                                break
                else:
                    #Runs only for the role name specified
                    for roles in roles['role_specification']:
                        aws_list = []
                        if roles['role_name'] == rolename:
                            print ("Role Name sent to playbook is: ", rolename)

                            roleFound = True

                            #Makes sure there is a trust policy
                            if roles['trust_policy'] is None:
                                print ("No trust policy for role: ", rolename)
                                continue

                            trust_policy_statement = roles['trust_policy']['Statement']

                            #Makes sure there is an aws trust policy
                            for statement in trust_policy_statement:
                                try:
                                    trust_policy_principal = statement['Principal']

                                    trust_policy_aws =  trust_policy_principal['AWS']

                                    #Adds the aws trust policy to the list in case there are multiple trusted relationships
                                    for aws in trust_policy_aws:
                                        if len(aws) == 1:
                                            aws_list.append(trust_policy_aws)
                                            break

                                        aws_list.append(aws)

                                except Exception as e:
                                        print ("No AWS policy in trust policy for role: ", rolename)

                            #Sends the target and source role name to the playbook for every aws trust policy
                            for item in aws_list:
                                trust_policy_role_name = item[item.index('/')+1:]

                                trust_policy_type = item[item.index('/')-4:item.index('/')]

                                if trust_policy_type == "role":
                                    extra_vars={
                                        "target_role_name": rolename,
                                        "source_role_name": trust_policy_role_name,
                                        "customer_name": kwargs.get("customer", None),
                                        "account_name": account_name,
                                        "verbosity": kwargs.get("verbosity", None),
                                        "debug_credentials": kwargs.get("debug_credentials", None),
                                    }
                                    cli.safe_playbook(
                                        role_playbook,
                                        is_static=True, # do not use dynamic inventory script, credentials may not be available
                                        **extra_vars
                                    )
        if not roleFound:
            print ("No roles with that name in that account or command. Run list command to see list of role names or use no rolename parameter to validate all roles" )



# Create the singleton for auto-discovery
command = Account()
