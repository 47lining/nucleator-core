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
from nucleator.cli.command import Command
import utils.input_utils as INP
import utils.generate_cert as GC
import re, os, json, boto, sys, stat, yaml
from boto import ec2
from jinja2 import Template

jenkins_keystore_password = 'P@ssw0rd'

class Setup(Command):
    """
    """

    name = "setup"

    @staticmethod
    def siteconfig_hascustomer(siteconfig, customer):
        customers = siteconfig['customers']
        for c in customers:
            if c['name'] == customer:
                return True
        return False

    @staticmethod
    def siteconfig_customer_hascage(siteconfig, customer, cage):
        customers = siteconfig['customers']
        for cust in customers:
            if cust['name'] == customer:
                return cage in cust['cages']

    @staticmethod
    def find_region_default_for(account_name, acct_list, aws_regions):
        for acct in acct_list:
            if account_name == acct['name']:
                reg = acct['default_region']
                return aws_regions.index(reg)
        return -1

    @staticmethod
    def find_account(account_name, acct_list):
        for acct in acct_list:
            if account_name == acct['name']:
                return acct
        return None

    @staticmethod
    def write_files(new_siteconfig, siteconfig_home, templates_home):
        for customer in new_siteconfig['customers']:
            with open (templates_home+'/{customer}-credentials.yml.j2', "r") as myfile:
                data = myfile.read()
            t = Template(data)
            output = t.render(account_list=customer['accounts'], customer_name=customer['name'],
                jenkins_keystore_password=jenkins_keystore_password, jenkins_java_keystore_password='changeit')
            with open (properties.NUCLEATOR_CONFIG_DIR+'/'+customer['name']+'-credentials.yml', "w") as myfile:
                myfile.write(output)
            try:
                # This method is only available on *some* Unix systems
                # If if fails, swallow the error.
                os.chmod(properties.NUCLEATOR_CONFIG_DIR+'/'+customer['name']+'-credentials.yml',
                    stat.S_IRUSR | stat.S_IWUSR)
            except:
                pass
            with open (templates_home+'/{customer}.yml.j2', "r") as myfile:
                data = myfile.read()
            t = Template(data)
            output = t.render(customer=customer)
            with open (siteconfig_home+'/'+customer['name']+'.yml', "w") as myfile:
                myfile.write(output)
            with open (templates_home+'/{customer}-{cage}.yml.j2', "r") as myfile:
                data = myfile.read()
            second_eight = 32
            for cage in customer['cages']:
                t = Template(data)
                output = t.render(cage_name=cage['name'], customer_name=customer['name'], second_eight=str(second_eight))
                with open (siteconfig_home+'/'+customer['name']+'-'+cage['name']+'.yml', "w") as myfile:
                    myfile.write(output)
                second_eight = second_eight + 1
                GC.generate_cert(customer['name']+'-'+cage['name'], cage['name'], customer['domain'], templates_home, siteconfig_home, jenkins_keystore_password=jenkins_keystore_password)

    @staticmethod
    def load_siteconfig(siteconfig_home):
        customer_pattern = re.compile('([a-zA-Z0-9]+)\.yml')
        cage_pattern = re.compile('([a-zA-Z0-9]+)-([a-zA-Z0-9]+)\.yml')
        customers = []
        listing = os.listdir(siteconfig_home)
        for files in listing:
            m = customer_pattern.match(files)
            if m:
                customers.append(m.group(1))
        siteconfig = {
            'customers': []
        }
        for cust in customers:
            if cust == 'main':
                continue
            cages = []
            # print "Customer: "+cust
            customer = { 'name': cust, 'cages': [] }
            listing = os.listdir(siteconfig_home)
            for files in listing:
                m = cage_pattern.match(files)
                if m and m.group(1) == cust:
                    cages.append(m.group(2))
            for c in cages:
                # print "\tCage: "+c
                customer['cages'].append(c)
            siteconfig['customers'].append(customer)
        return siteconfig

    def wizard(self, **kwargs):
        """
        3. Enter the name of your first Nucleator customer (quickstart):
        4. Enter the DNS subdomain where Nucleator Cages should be created for this customer
            (quickstart.yourcompany.com):
        5. Choose a default region for Nucleator Cages (us-east-1):
        2. Enter a friendly name for AWS account #123456789012 (main):
        1. Enter your AWS account # (123456789012):
        6. Enter a comma-separated list of cages that you would like Nucleator to be able to
            provision (build, poc):
        7. Confirm the Availability zones available for VPC Subnets in the us-east-1 region in
           Account main. See http://47lining.github.io/nucleator/az.html for details
           (us-east-1a, us-east-1c):
        8. Enter IAM User Credentials AWS_ACCESS_KEY_ID for NucleatorUser in Account main:
        9. Enter IAM User Credentials AWS_SECRET_ACCESS_KEY for NucleatorUser in Account main:
        From the answers, together with some simplifying assumptions for the initial config,
        we could spit out the right files in the right places, which the user could choose to
        extend over time.

        Tests / Validation
        valid customer_name and account_name
        test for existence of files that will be written. Bail if present unless invoked with --force option.
        do we need any validation on cage names?

        Data structure:
            account:
                name
                access_key
                secret_key
                aws_number
            cage:
                name
                account_name
                region
                owner

        Resulting Files
        ~/.nucleator/<customer_name>-credentials.yml
        ~/.nucleator/siteconfig/<customer_name>.yml
        ~/.nucleator/siteconfig/<customer_name>-<cage_name_1>.yml
        ...
        ~/.nucleator/siteconfig/<customer_name>-cage_name_n>.yml
        """
        do_validation = kwargs.get("validate", None)
        if do_validation is None:
            do_validation = True

        cont = INP.ask_yesno("This wizard creates a Nucleator siteconfig for one or more Customers, AWS Accounts and Cages in the current directory", True)
        if not cont:
            sys.exit(-1)
        # siteconfig_home = os.path.join(properties.NUCLEATOR_CONFIG_DIR, 'siteconfig')
        # Generate the config files in the current directory
        siteconfig_home = "."
        templates_home =  os.path.join(os.path.dirname(__file__), '..', 'templates')
        siteconfig = self.load_siteconfig(siteconfig_home)
        new_siteconfig = {
            'customers': []
        }
        first_cust = True
        while True:
            customer_name = None
            if first_cust:
                customer_name = INP.ask_string("Please enter a customer name", 'quickstart', 
                help_msg="The name which will be used to group cages and stackets")
            else:
                customer_name = INP.ask_string("Please enter another customer name or press Enter if you are done", '', 
                help_msg="The name which will be used to group cages and stackets")
            if customer_name is None or len(customer_name)==0:
                break
            if self.siteconfig_hascustomer(siteconfig, customer_name):
                over = INP.ask_yesno("Sorry, that customer is already present, overwrite? ", False)
                if not over:
                    continue
            error_msg = utils.validate_customer(customer_name)
            if error_msg:
                print error_msg
                continue
            first_cust = False
            domain = INP.ask_string("What is the domain you will be using? ", customer_name+".com", 
                help_msg="The top level domain which will provide the address for your applications.")
            customer = { 'name': customer_name, 'domain': domain, 'cages': [], 'accounts': [] }
            print "OK, first let's do some accounts..."
            first_account = True
            while True:
                account_name = None
                if first_account:
                    account_name = INP.ask_string("Please enter an account name",
                    'main', "This is a helper name you give to a specific AWS account")
                else:
                    account_name = INP.ask_string("Please enter another account name or press enter if done",
                    '', "This is a helper name you give to a specific AWS account")
                if account_name is None or len(account_name)==0:
                    break
                error_msg = utils.validate_account(account_name)
                if error_msg:
                    print error_msg
                    continue
                first_account = False
                while True:
                    if "ACCESS_KEY" in os.environ:
                        access_key = os.environ["ACCESS_KEY"]
                    else:
                        access_key = INP.ask_string("What is the access key for account '"+account_name+"'")
                    if "SECRET_KEY" in os.environ:
                        secret_key = os.environ["SECRET_KEY"]
                    else:
                        secret_key = INP.ask_string("What is the secret key for account '"+account_name+"'")
                    if do_validation:
                        conn = ec2.connection.EC2Connection(aws_access_key_id=access_key, aws_secret_access_key=secret_key)
                        try:
                            print ("Checking with AWS... "),
                            reg_array = conn.get_all_regions()
                            # [RegionInfo:eu-central-1, RegionInfo:sa-east-1,
                            aws_regions = ['us-east-1', 'us-west-2', 'eu-west-1']
                            # for r in reg_array:
                                # aws_regions.append(str(r.name))
                            # print ("OK, you have "+str(len(reg_array))+" regions available.")
                            print ("OK, that looks good.")
                            break
                        except boto.exception.EC2ResponseError as err:
                            print "AWS doesn't recognize your access and/or secret key"
                    else:
                        break
                aws_number = INP.ask_number("What is the AWS account number for account '"+account_name+"'? ")
                default_region = INP.multiple_choice("Choose a default region for Nucleator Cages ",
                        aws_regions, 1, "This will be the default region where your cages will be created")
                customer['accounts'].append({ 'name': account_name, 'access_key': access_key,
                     'secret_key': secret_key, 'default_region': default_region, 'aws_number': aws_number,
                     'aws_regions': aws_regions})
            print "Now, the cages to provision and configure..."
            accounts = []
            for acct in customer['accounts']:
                accounts.append(acct['name'])
            first_cage = True
            while True:
                cage_name = None
                if first_cage:
                    cage_name = INP.ask_string("Please enter a cage name", 'build')
                else:
                    cage_name = INP.ask_string("Please enter another cage name or press enter if you are done", '')
                if cage_name is None or len(cage_name)==0:
                    break
                if self.siteconfig_customer_hascage(siteconfig, customer_name, cage_name):
                    over = INP.ask_yesno("Sorry, that cage exists for this customer, overwrite?", False)
                    if not over:
                        continue
                error_msg = utils.validate_cage(cage_name)
                if error_msg:
                    print error_msg
                    continue
                first_cage = False
                account_name = INP.multiple_choice("Which account will own this cage? ", accounts, 1)
                this_account = self.find_account(account_name, customer['accounts'])
                default_region_number = self.find_region_default_for(account_name, customer['accounts'], 
                    this_account['aws_regions'])
                region = INP.multiple_choice("Which region? ", aws_regions, default_region_number+1)
                owner = INP.ask_string("Who is the owner of this cage", 'exampleUser')
                customer['cages'].append({ 'name': cage_name, 'account_name': account_name,
                    'region': region, 'owner': owner})

            accounts_map = {}
            for cage in customer['cages']:
                if cage['account_name'] not in accounts_map:
                    accounts_map[cage['account_name']] = []
                if cage['region'] not in accounts_map[cage['account_name']]:
                    accounts_map[cage['account_name']].append(cage['region'])
            for account in customer['accounts']:
                regions = accounts_map[account['name']]
                region_map = []
                for reg in regions:
                    conn = ec2.connect_to_region(reg, aws_access_key_id=account['access_key'], aws_secret_access_key=account['secret_key'])
                    zone_list = conn.get_all_zones()
                    # [Zone:us-east-1b, Zone:us-east-1c, Zone:us-east-1d, Zone:us-east-1e]
                    az_list = []
                    i = 1
                    for zone in zone_list:
                        if zone.state == 'available':
                            # print "For "+reg+", adding "+str(zone.name)
                            az_list.append("AZ"+str(i)+": "+zone.name)
                            i = i + 1
                    region_map.append({ 'name': reg, 'az_list': az_list})
                account['map_regions']=region_map

            new_siteconfig['customers'].append(customer)

        # print json.dumps(new_siteconfig, sort_keys=True, indent=4, separators=(',', ': '))
        self.write_files(new_siteconfig, siteconfig_home, templates_home)

        return 0

    def show(self, **kwargs):
        """
        Look at the list of siteconfig files and give a 'nice' display
        """
        siteconfig_home = os.path.join(properties.NUCLEATOR_CONFIG_DIR, 'siteconfig')
        siteconfig = self.load_siteconfig(siteconfig_home)
        print json.dumps(siteconfig, sort_keys=True, indent=4, separators=(',', ': '))
        return 0

    def validate_keys(self, home_dir):
        # Read the sources.yml and distkeys.yml
        # For each entry in sources.yml, is there a host in distkeys.yml?
        sources = None
        if not os.path.isfile(os.path.join(home_dir, "sources.yml")):
            print "There is no definition file 'sources.yml' in "+home_dir
        else:
            sources = yaml.load(open(os.path.join(home_dir, "sources.yml")))
        distkeys = None
        if not os.path.isfile(os.path.join(home_dir, "distkeys.yml")):
            print "There is no definition file 'distkeys.yml' in "+home_dir
        else:
            distkeys = yaml.load(open(os.path.join(home_dir, "distkeys.yml")))
        if sources and distkeys:
            for src in sources:
                # src, version, name
                # check hostname in src present in distkeys
                is_found = False
                for key in distkeys['distribution_keys']:
                    if src['src'] in key['hostname']:
                        is_found = True
                        break
                if not is_found:
                    print "No entry in distkeys for "+src['name']+" ("+src['src']+"), should be public."
                else:
                    print src['name']+" has distkey."
        # For each entry in distkeys.yml, does the key file exist?
        if distkeys:
            for key in distkeys['distribution_keys']:
                # hostname, ssh_config_host, private_keyfile
                if not os.path.isfile(os.path.join(home_dir, "distkeys", key['private_keyfile'])):
                    print "There is no key file '"+key['private_keyfile']+"' in "+home_dir+"/distkeys"
                else:
                    print key['hostname']+" keyfile exists..."

    def validate_cages(self, siteconfig_home, customer):
        # Read the customer.yml
        # For each cage, see if there's a customer-cage.yml, but not much to check in it.
        print "Checking cages for customer "+customer['name']
        customer_yaml = yaml.load(open(os.path.join(siteconfig_home, customer['name']+".yml"), 'r'))
        for cage in customer['cages']:
            if cage not in customer_yaml['cage_names']:
                print "There is no definition for cage "+cage+" in the "+customer['name']+".yml file"
            if not os.path.isfile(os.path.join(siteconfig_home, customer['name']+"-"+cage+".yml")):
                print "There is no definition file for customer "+customer['name']+", cage "+cage
            if 'aws_accounts' not in customer_yaml:
                print "You need to define accounts in 'aws_accounts' in "+customer['name']+".yml"
            else:
                if 'region' not in customer_yaml['cage_names'][cage]:
                    print "You should define the region for cage "+cage
                if 'owner' not in customer_yaml['cage_names'][cage]:
                    print "You should define the owner for cage "+cage
                if 'account' not in customer_yaml['cage_names'][cage]:
                    print "You need to define the account for cage "+cage
                else:
                    if customer_yaml['cage_names'][cage]['account'] not in customer_yaml['aws_accounts']:
                        print "The account "+customer_yaml['cage_names'][cage]['account']+" for cage "+cage+" needs to be included in 'aws_accounts'"
                    else:
                        print "Cage "+cage+" looks good."

    def validate(self, **kwargs):
        """
        Read the siteconfig and other(?) things to attempt to detect issues
        """
        siteconfig_home = kwargs.get("siteconfig_dir", None)
        if siteconfig_home:
            if not os.path.isdir(siteconfig_home):
                print "Directory doesn't exist: "+siteconfig_home
                return 0
        else:
            siteconfig_home = os.path.join(properties.NUCLEATOR_CONFIG_DIR, 'siteconfig')
        siteconfig = self.load_siteconfig(siteconfig_home)
        print "Validation Step 1: Are the Cages in your yml files all described?"
        for customer in siteconfig['customers']:
            self.validate_cages(siteconfig_home, customer)
        print "Validation Step 2: Check your distkeys.yml for existence of all the keys"
        self.validate_keys(properties.NUCLEATOR_CONFIG_DIR)
        return 0

    def parser_init(self, subparsers):
        """
        Initialize parsers for this command.
        """
        # add parser for cage command
        setup_parser = subparsers.add_parser('setup')
        setup_subparsers=setup_parser.add_subparsers(dest="subcommand")

        # wizard subcommand
        setup_wizard=setup_subparsers.add_parser('wizard', help="create a siteconfig")
        setup_wizard.add_argument("--validate", required=False, help="Validate entries with AWS")

        # show subcommand
        setup_subparsers.add_parser('show', help="show a siteconfig")
        # validate subcommand
        validater = setup_subparsers.add_parser('validate', help="validate a siteconfig")
        validater.add_argument("--siteconfig_dir", required=False, help="Siteconfig directory to check (Default ~/.nucleator/siteconfig)")

# Create the singleton for auto-discovery
command = Setup()
