# pip install pytest
# python -m pytest test/test_parse_cluster.py
# without these, the import gets hosed in the ansible modules
import ansible
from ansible.vars.unsafe_proxy import wrap_var
from ansible.vars.unsafe_proxy import UnsafeProxy
import ansible.template
# from ansible.template import Templar
from core.foundation.ansible.action_plugins.bastion_ssh_config  import ActionModule

class MockContextObject(object):
    pass

class MockConnectionObject(object):
    pass

def test_build_customers():
    # bsc = ActionModule(task, connection, play_context, loader, templar, shared_loader_obj)
    bsc = ActionModule(None, None, None, None, None, None)
    task_vars = {
        "ansible_play_hosts_all": [u'bastion.build.test4.47lining.com', u'nat.build.test4.47lining.com'],
        "ansible_play_hosts": [u'bastion.build.test4.47lining.com', u'nat.build.test4.47lining.com'],
        "ansible_current_hosts": [u'bastion.build.test4.47lining.com', u'nat.build.test4.47lining.com'],
        "play_hosts": [u'bastion.build.test4.47lining.com', u'nat.build.test4.47lining.com'],
        "hostvars": {
            "bastion.build.test4.47lining.com": {
                "ec2_tag_NucleatorCustomer": "test4",
                "ec2_tag_NucleatorCage": "build"
            },
            "nat.build.test4.47lining.com": {
                "ec2_tag_NucleatorCustomer": "test4",
                "ec2_tag_NucleatorCage": "build"
            }
        }
    }
    customers = bsc.build_customers(task_vars)
    with open("test.out", "w") as f:
        f.write(str(customers))
        f.write('\n')
    assert(customers)
    # assert(msg == "rs1")

def test_ssh_config():
    bsc = ActionModule(None, None, None, None, None, None)
    customers = {
        "test4": {"build": [u'bastion.build.test4.47lining.com', u'nat.build.test4.47lining.com']}
    }
    customer_name = "test4"
    cage_name = "build"
    tmp = None
    failed=False
    changed=False
    result = {}
    complex_args = {
        "dest": "/tmp/ssh_config.out",
        "identity_file": "~/.ssh/47lining-test4-us-west-2.pem"
    }
    result, config = bsc.ssh_config(customers, customer_name, cage_name, tmp, task_vars, result, complex_args=complex_args)
    with open("test.out", "wa") as f:
        f.write(str(result))
        f.write('\n')
        f.write(str(config))
        f.write('\n')
    assert(len(result)==0)
    assert(len(config)>0)
    # assert(msg == "rs1")

def test_materialize():
    context = MockContextObject()
    context.check_mode = False
    context.no_log = False
    context.diff = False
    connection = MockConnectionObject()
    connection.module_implementation_preferences = {}

    bsc = ActionModule(None, connection, context, None, None, None)
    result = {}
    config_dest = "/tmp/bsc.out"
    result = bsc.materialize_results(config_dest, config_file_content, "~/.nucleator/ssh-config", task_vars, result)
    assert(len(result) == 0)

# def test_clustercharsbad():
#     r, msg = parse_cluster("action cluster rs-one")
#     assert(r)
#     assert(msg == "rs-one")

config_file_content = """#---------------------------------------------------------------------------------------------------------------------------------------------#
# Nucleator SSH Config
#---------------------------------------------------------------------------------------------------------------------------------------------#
Host *
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
    TCPKeepAlive=yes
    ServerAliveInterval 15
    ServerAliveCountMax 16

#---------------------------------------------------------------------------------------------------------------------------------------------#

# bastion-build-public
Host bastion.build.test4.47lining.com
        Hostname bastion.build.test4.47lining.com
        User ec2-user
        IdentityFile ~/.ssh/47lining-test4-us-west-2.pem

#---------------------------------------------------------------------------------------------------------------------------------------------#

# bastion-build
Host bastion-build
        Hostname 172.24.0.1
        User ec2-user
        IdentityFile ~/.ssh/47lining-test4-us-west-2.pem
        ProxyCommand ssh -F /tmp/ssh_config.out/test4/build ec2-user@bastion.build.test4.47lining.com nc %h %p

# bastion-build
Host 172.24.0.1
        Hostname 172.24.0.1
        User ec2-user
        IdentityFile ~/.ssh/47lining-test4-us-west-2.pem
        ProxyCommand ssh -F /tmp/ssh_config.out/test4/build ec2-user@bastion.build.test4.47lining.com nc %h %p

# nat-build
Host nat.build.test4.47lining.com
        Hostname 172.24.0.2
        User ec2-user
        IdentityFile ~/.ssh/47lining-test4-us-west-2.pem
        ProxyCommand ssh -F /tmp/ssh_config.out/test4/build ec2-user@bastion.build.test4.47lining.com nc %h %p

# nat-build
Host nat-build
        Hostname 172.24.0.2
        User ec2-user
        IdentityFile ~/.ssh/47lining-test4-us-west-2.pem
        ProxyCommand ssh -F /tmp/ssh_config.out/test4/build ec2-user@bastion.build.test4.47lining.com nc %h %p

# nat-build
Host 172.24.0.2
        Hostname 172.24.0.2
        User ec2-user
        IdentityFile ~/.ssh/47lining-test4-us-west-2.pem
        ProxyCommand ssh -F /tmp/ssh_config.out/test4/build ec2-user@bastion.build.test4.47lining.com nc %h %p

"""
task_vars = {
    "ansible_play_hosts_all": [u'bastion.build.test4.47lining.com', u'nat.build.test4.47lining.com'],
    "ansible_play_hosts": [u'bastion.build.test4.47lining.com', u'nat.build.test4.47lining.com'],
    "ansible_current_hosts": [u'bastion.build.test4.47lining.com', u'nat.build.test4.47lining.com'],
    "play_hosts": [u'bastion.build.test4.47lining.com', u'nat.build.test4.47lining.com'],
    "hostvars": {
        "bastion.build.test4.47lining.com": {
            "ec2_private_ip_address": "172.24.0.1"
        },
        "nat.build.test4.47lining.com": {
            "ec2_private_ip_address": "172.24.0.2"
        },
        "localhost": {
            "customer_domain": "test4.47lining.com"
        }
    }
}
