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
import os, sys
sys.path.insert(0,'..')
import commands.setup as SC
import commands.utils.generate_cert as GC
from nucleator.cli import properties
from nucleator.cli import utils

GC.generate_cert("47lining-build", "build", "47lining.com", "../templates", ".", "P@ssw0rd")

# setup_home = os.path.join(properties.NUCLEATOR_CONFIG_DIR, 'setup')
# setup = SC.command.load_setup(setup_home)

# has = SC.command.setup_hascustomer(setup, '47lining')
# if not has:
# 	print "Siteconfig missing 47lining"
# has = SC.command.setup_customer_hascage(setup, '47lining', 'build')
# if not has:
# 	print "Siteconfig missing 47lining.build"
# has = SC.command.setup_customer_hascage(setup, '47lining', 'BOGUS')
# if has:
# 	print "Siteconfig found 47lining.BOGUS"
# has = SC.command.setup_hascustomer(setup, 'BOGUS')
# if has:
# 	print "Siteconfig found bogus customer"

# val = utils.validate_customer("customer_name")
# if val:
# 	print val

# val = utils.validate_customer("47lining")
# if val:
# 	print val

# val = utils.validate_account("47lining")
# if val:
# 	print val

# val = utils.validate_cage("47lining")
# if val:
# 	print val
