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
from nucleator.cli import properties
from nucleator.cli import utils
from nucleator.cli import unbuffered_subprocess as usp

import os, subprocess, uuid

class Update(Command):
    
    name = "update"
    
    def parser_init(self, subparsers):
        """
        Initialize parsers for this command.
        """
        init_parser = subparsers.add_parser('update')

    def update(self, **kwargs):
        """
        The update command:

          - Pulls and installs Nucleator Cage and Stackset modules to contrib dir in 
            Nucleator configuration directory, as specified in manifest

          - Recursively pulls dependent modules specified in module dependencies for 
            each module in manifest
        """

        self.update_sources(**kwargs)
        self.update_roles(**kwargs)

        utils.write("SUCCESS - successfully updated nucleator sources and ansible roles, placed in {0}\n\n".format(properties.contrib_path()))


    def update_sources(self, **kwargs):
        """
        update Nucleator stacksets specified in sources.yml
        pull each one into ~/.nucleator/contrib/
        """
        sources = os.path.join(properties.NUCLEATOR_CONFIG_DIR, "sources.yml")
        utils.write("\nUpdating nucleator commands from sources in {0}\n".format(sources))
        try:
            roles_path_tmp=os.path.join(properties.NUCLEATOR_CONFIG_DIR, "-".join( [ "contrib", str(uuid.uuid4()) ] ))
            update_command = [
                "ansible-galaxy", "install",
                "--force",
                "--role-file", sources,
                "--roles-path", roles_path_tmp,
            ]
            utils.write(" ".join(update_command) + "\n")

            os.environ["PYTHONUNBUFFERED"]="1"
            update_process=usp.Popen(
                update_command,
                shell=False,
                stdout=usp.PIPE,
                stderr=usp.PIPE
            )
            update_out, update_err = update_process.communicate()
            update_rc = update_process.returncode

        except Exception, e:
            utils.write_err("Exception while updating nucleator commands from specified sources:\n{0}".format(e), False)
            raise e

        # move new contrib stacksets into place
        utils.write("\nMoving updated nucleator commands into place\n")

        try:
            # test for existence of config dir
            roles_path=os.path.join(properties.NUCLEATOR_CONFIG_DIR, "contrib")
            if not os.path.isdir(roles_path):
                move_sequence = "mv {1} {0}".format(roles_path, roles_path_tmp)
            else:
                bak_dir=os.path.join(properties.NUCLEATOR_CONFIG_DIR, "contrib.bak")
                roles_path_bak=os.path.join(bak_dir, "-".join( [ "contrib.bak", str(uuid.uuid4()) ]))
                move_sequence = "mkdir -p {0} && mkdir -p {1} && mv {1} {2} && mv {3} {1}".format(bak_dir, roles_path, roles_path_bak, roles_path_tmp)

            utils.write(move_sequence + "\n")
            os.environ["PYTHONUNBUFFERED"]="1"
            move_process=usp.Popen(
                move_sequence,
                shell=True,
                stdout=usp.PIPE,
                stderr=usp.PIPE
            )
            move_out, move_err = move_process.communicate()
            move_rc = move_process.returncode
        except Exception, e:
            utils.write_err("Exception while moving updated nucleator commands into place:\n{0}".format(e), False)
            raise e
                
        if update_rc != 0:
            utils.write_err("Received non-zero return code {0} while attempting to update from nucleator sources using command: {1}\n\ncaptured stderr:\n{2}\n\n exiting with return code 1...".format(update_rc, " ".join(update_command), update_err))
        elif move_rc !=0:
            utils.write_err("Received non-zero return code {0} while attempting to move updated nucleator sources into place using command: {1}\n\ncaptured stderr:\n{2}\n\n exiting with return code 1...".format(move_rc, move_sequence, move_err))
        
        return 0

    def update_roles(self, **kwargs):
        """
        Use ansible-galaxy to install Ansible roles and any role dependencies
        specified in ansible/roles/roles.yml for any installed Nucleator Stackset.
        """

        utils.write("\nUpdating ansible roles specified in installed Nucleator Stacksets using ansible-galaxy.\n")
        cli=Command.get_cli(kwargs)
        cli.import_commands(os.path.join(properties.NUCLEATOR_CONFIG_DIR,"contrib"))
        
        path_list = cli.ansible_path_list("roles", isdir=True)
        for roles_path in path_list:
            sources = os.path.join(roles_path, "roles.yml")
            if os.path.isfile(sources):
                # import roles using ansible galaxy
                update_command = [
                    "ansible-galaxy", "install",
                    "--force",
                    "--role-file", sources,
                    "--roles-path", roles_path,
                ]
                utils.write(" ".join(update_command) + "\n")
                os.environ["PYTHONUNBUFFERED"]="1"
                try:
                    update_process=usp.Popen(
                    update_command,
                    shell=False,
                    stdout=usp.PIPE,
                    stderr=usp.PIPE
                    )
                    update_out, update_err = update_process.communicate()
                    update_rc = update_process.returncode

                except Exception, e:
                    utils.write_err("Exception while updating ansible roles from specified sources:\n{0}".format(e), False)
                    raise e

                if update_rc != 0:
                    utils.write_err("Received non-zero return code {0} while attempting to update ansible roles from specified sources using command: {1}\n\ncaptured stderr:\n{2}\n\n exiting with return code 1...".format(update_rc, " ".join(update_command), update_err))

        return 0

# Create the singleton for auto-discovery
command = Update()

