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
from utils import get_clean

def core_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core"))

def contrib_path():
    return os.path.abspath(NUCLEATOR_CONTRIB_DIR)

HOME=get_clean("HOME")

NUCLEATOR_CORE=core_path()
ANSIBLE_LOCATION=os.path.join(NUCLEATOR_CORE, "foundation", "ansible")
ANSIBLE_CONFIG=get_clean("ANSIBLE_CONFIG", os.path.join(ANSIBLE_LOCATION, "ansible.cfg"))

NUCLEATOR_CONFIG_DIR=get_clean("NUCLEATOR_CONFIG_DIR", os.path.join(HOME, ".nucleator"))
NUCLEATOR_CONTRIB_DIR=os.path.join(NUCLEATOR_CONFIG_DIR, "contrib")

DYNAMIC_HOSTS_SRC = os.path.join(ANSIBLE_LOCATION, "dynamic_hosts")

DYNAMIC_HOSTS_PATH = os.path.join(NUCLEATOR_CONFIG_DIR, "inventory")
STATIC_HOSTS_PATH=os.path.join(DYNAMIC_HOSTS_PATH, "static_hosts")
BOOTSTRAP_HOSTS_PATH=os.path.join(DYNAMIC_HOSTS_SRC, "static_hosts")

EC2_INI="ec2.ini.private"
EC2_INI_PATH=os.path.join(ANSIBLE_LOCATION, EC2_INI)
