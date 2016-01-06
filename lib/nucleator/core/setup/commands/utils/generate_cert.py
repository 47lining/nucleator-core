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
import os, shlex
from jinja2 import Template
from subprocess import Popen, PIPE

def generate_cert(file_name, cage_name, customer_domain, templates_home, siteconfig_home,
    pkcs12_bundle_password, debug=False):
    # Erase previous files
    if os.path.isfile("openssl.cfg"):
        os.remove("openssl.cfg")
    if os.path.isfile(file_name+".pem"):
        os.remove(file_name+".pem")
    if os.path.isfile(file_name+".crt"):
        os.remove(file_name+".crt")
    if os.path.isfile(file_name+".509"):
        os.remove(file_name+".509")

    # Write out an openssl.cfg
    with open (templates_home+'/openssl.cfg.j2', "r") as myfile:
        data = myfile.read()
    t = Template(data)
    output = t.render(customer_domain=customer_domain, file_name=file_name, cage_name=cage_name,
        pkcs12_bundle_password=pkcs12_bundle_password)
    with open (siteconfig_home+'/openssl.cfg', "w") as myfile:
        myfile.write(output)

    print "Generating key and x509 cert"
    # openssl x509 -req -days 365 -in $cert_name.csr -signkey $keypair_name -out $cert_name.crt
    cmd = "openssl req -x509 -newkey rsa:2048 -keyout "+file_name+".pem -out "+file_name+".509 -days 365 -config openssl.cfg"
    Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, stdin=PIPE).wait()

    print "Converting to pkcs12"
    # openssl pkcs12 -export -in $cert_name.crt -inkey $keypair_name -out $cert_name.p12 -name $cert_name-cert -CAfile ca.crt -caname root -password pass:$keystore_password
    cmd = "openssl pkcs12 -export -in "+file_name+".509 -inkey "+file_name+".pem -out "+file_name+".crt -name "+file_name+"-cert -CAfile ca.crt -caname root -password pass:P@ssw0rd -passin pass:P@ssw0rd"
    Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, stdin=PIPE).wait()

    if not os.path.isfile(file_name+".crt"):
        print "Something went worng"
    else:
        # clean up temp files
        if not debug:
            if os.path.isfile("openssl.cfg"):
                os.remove("openssl.cfg")
            if os.path.isfile(file_name+".pem"):
                os.remove(file_name+".pem")
            if os.path.isfile(file_name+".509"):
                os.remove(file_name+".509")
    return
