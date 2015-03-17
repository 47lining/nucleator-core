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

from nucleator.cli import properties
from nucleator.cli import utils
import sys, os, argparse

class Cli(object):
    """
    An object and helper methods to represent an installation of Nucleator
    """

    def __init__(self):
        self.commands = {}
        self.command_paths = []

        # Setup the root argument parser
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("-v", "--verbosity", required=False, action="count", help="Increase output verbosity")
        self.parser.add_argument("-p", "--preview", required=False, action="store_true", 
                                 help="Display information about what a command will do, without actually executing the command.\n" +
                                      "The --preview flag should come before any subcommands on the command line.")
        self.subparsers = self.parser.add_subparsers(dest="command")
        
    def core_path(self):
        """path to to core commands installed with Nucleator"""
        return properties.core_path()

    def contrib_path(self):
        """path to to contrib commands, added by user via Nucleator's update command"""
        return properties.contrib_path()

    def import_commands(self, path):

        if not os.path.isdir(path):
            # skip if path to import doesn't exist
            return

        sys.path.append(path)

        # iterate through nucleator command definitions found as immediate subdirs of path
        for command_dir in next(os.walk(path))[1]:

            self.command_paths.append(os.path.join(path,command_dir))
            candidate_location = os.path.join(path, command_dir, "commands")
            import_candidates = os.listdir(candidate_location) if os.path.isdir(candidate_location) else []

            # iterate through filtered import candidates
            for name in [n for n in import_candidates
                         if n.endswith('.py') and n != "__init__.py"]:
                name = name.replace('.py', '')
                module = __import__(
                    "{0}.commands.{1}".format(command_dir, name),
                    fromlist=['']
                )
                command = getattr(module, "command", None)
                if command is None:
                    utils.write_err("Invalid command implementation (%s)" % name)
                command.parser_init(self.subparsers)
                self.commands[command.name] = command

    def parse(self):
        self.opts = vars(self.parser.parse_args())
        self.opts["verbose"] = self.opts.get("verbosity", 0) > 0
        self.opts["cli"] = self
        return self.opts

    def current_command_name(self):
        return self.opts.get("command")

    def get_nucleator_command(self, command_name):
        return self.commands[command_name]

    def current_nucleator_command(self):
        return self.get_nucleator_command(self.current_command_name())

    def execute(self):
        self.current_nucleator_command().execute(**self.opts)

    def dump(self):
        utils.write ("{0}{1}".format(self.current_command_name(), os.linesep))
        import json
        utils.write (
            "{0}{1}".format(
                json.dumps(
                    {k:v for (k,v) in self.opts.iteritems() if k != "cli"},
                    self.opts,
                    sort_keys=True,
                    indent=4, separators=(',', ': ')
                ),
                os.linesep
            )
        )
