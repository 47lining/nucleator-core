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

import os
import inspect
import webbrowser

class Command(object):
    """
    An abstract base class that demonstrates the interface a command must implement.
    """
    
    # All commands must have a name attribute
    name = "command name"

    def parser_init(self, subparsers):
        """
        Initialize the command by adding appropriate sub-parsers to the root command sub-parsers.
        """
        pass
    
    def execute(self, **kwargs):
        """
        Execute the command using the data dictionary parsed from the command line. Because 
        command / subcommand is a common pattern, this base implementation first looks for the 
        presence of 'subcommand' in the input, and if found will automatically dispatch to
        a method on the instance matching the name of the subcommand.  If no subcommand is
        present in the input, this base implementation looks for the presence of a 'command'
        in the input, and if found will dispatch to a method on the instance matching the name
        of the command.
        """

        directive = kwargs.get("subcommand", kwargs.get("command", None))
        subsubcommand = kwargs.get("subsubcommand", None)
        if directive and subsubcommand:
            directive = "_".join( [directive, subsubcommand] )
        if not directive:
            raise ValueError("unable to find command or subcommand!")

        method = getattr(self, directive, None)
        if method is None:
            raise ValueError("no method found that matches specified subcommand or command!")

        if kwargs.get("preview"):
            # We just want to display information about what the command will do, without actually
            # running the command. By convention, we use the callable's docstring as the string to
            # display on the command line output.
            doc = getattr(method, "__doc__", "There is no preview information available for this command.")
            print doc
            
            # If the command supports cost estimation we print out the URL to the cost estimate in 
            # the AWS cost estimation tool. By convention we look for a <directive>_cost_est method
            # on the command and call it if it exists.
            est_method = getattr(self, "%s_cost_est" % directive, None)
            if est_method is not None:
                url = est_method()
                print
                print "An AWS cost estimate for the resources created by this command can be accessed at:"
                print url
                print
                #webbrowser.open(url.strip())
            return

        return method(**kwargs)

    @staticmethod
    def get_cli(kwargs):
        cli=kwargs.get("cli", "None")
        if cli is None:
            raise ValueError("INTERNAL ERROR: cli should have been set by upstream code, but is not specified")
        return cli

    def get_command_dir(self):
        return os.path.dirname(os.path.abspath(inspect.getfile(self.__class__)))

    def get_command_playbook(self, name):
        """Get the absolute path to one of this command's playbooks, with the given name"""
        return os.path.abspath(os.path.join(self.get_command_dir(), "..", "ansible", name))

    def get_command_ansible_path(self, subpath, isdir=False):
        """Get the absolute path to a provide subpath relative to this command's ansible directory"""

        candidate=os.path.abspath(
            os.path.join(
                self.get_command_dir(),
                "..",
                "ansible",
                subpath,
            )
        )
        return candidate if (not isdir and os.path.isfile(candidate)) or (isdir and os.path.isdir(candidate)) else None
