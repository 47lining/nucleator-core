#!/usr/bin/env python
#
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

import sys, os
from glob import glob

sys.path.insert(0, os.path.abspath('lib'))
from nucleator import __version__

try:
    from setuptools import setup, find_packages
except ImportError:
    print "Nucleator requires setuptools in order to build. " \
          "Install it using your package manager (usually python-setuptools) or via pip (pip install setuptools)."
    sys.exit(1)

coredir = os.path.join('lib','nucleator','core')
corefiles=[]
for d, folders, files in os.walk(coredir):
    for f in files:
        corefiles.append(os.path.join(os.path.sep.join(d.split(os.path.sep)[2:]),f))

from setuptools.command.install import install

class custom_install(install):
    def run(self):
        install.run(self)

        # The EC2 dynamic inventory generator is GPL3 so we can't pack it in with nucleator
        import httplib2 # should be installed by now
        srcurl = "https://raw.githubusercontent.com/47lining/inventory/master/library/ec2.py"
        target = os.path.join(self.install_lib, "nucleator", "core", "foundation", "ansible", "dynamic_hosts", "ec2.py")
        resp, content = httplib2.Http().request(srcurl)
        cmdfile = open(target, "w")
        cmdfile.write(content)
        cmdfile.close()
        os.system("chmod ugo+x %s" % target)


        

setup(name='nucleator',
      cmdclass={'install': custom_install},
      zip_safe=False,
      version=__version__,
      description='Cloud automation tools',
      author="47Lining",
      author_email='info@47lining.com',
      url='http://www.47lining.com/',
      license='Apache 2.0',
      install_requires=['setuptools', 'pycrypto >= 2.6', 'graffiti_monkey == 0.7', 'paramiko', 'pyyaml', 'jinja2', 'awscli', 'httplib2', 'boto >= 2.34.0'],
      package_dir={ 'nucleator': 'lib/nucleator' },
      package_data={ 'nucleator': corefiles },
      packages=find_packages('lib'),
      scripts=[
         'bin/nucleator'
      ],
      data_files=[],
)
