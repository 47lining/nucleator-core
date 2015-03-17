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
import commands.utils.generate_cert as GC
import commands.utils.input_utils as INP
from nucleator.cli import properties
from nucleator.cli import utils

cage = INP.ask_string("Cage name", "build")
customer = INP.ask_string("Customer", "47lining")
domain = INP.ask_string("Domain", customer+".com")

GC.generate_cert(customer+"-"+cage, cage, domain, "../templates", ".", "P@ssw0rd", True)
# def generate_cert(file_name, cage_name, customer_domain, templates_home, siteconfig_home, debug=False):
