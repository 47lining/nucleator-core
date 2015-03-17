Nucleator
=========

Nucleator allows you to easily create and manage secure, scalable 
environments in Amazon Web Services (AWS), into which reusable stacks of 
components can be deployed to address common cloud usage scenarios, for 
example:

  - Establishing a continuous integration framework with the desired 
    deployment environments, deployment targets, and required security, 
    high-availability and scaling characteristics

  - Highly available and scalable application configurations

  - On-demand EMR or Redshift cluster deployments

Nucleator makes it easy to partition your environments across multiple AWS 
accounts and to leverage a supported and maintained set of CloudFormation 
stacks that work together to allow you to focus on your core problems.


Nucleator Benefits
------------------

*Instant AWS Productivity*

Reduces bootstrapping time for new customers with new AWS Accounts to productive usage.

*More than Infrastructure as Code - Operations as Code*

 - High-level operational building blocks required to quickly realize cloud 
   workloads in response to business needs

  - Provides key operational / SOP interfaces that lower level CM tools (Puppet, 
    Chef, Ansible, OpsWorks) leave unaddressed on their own

*Embedded, Reviewed Best Practices Usage*

  - Security

  - High Availability

  - Scalability

  - Resource tagging and cost Reporting

*Strong Cross-Account Support*

  - Partition Disparate workloads into distinct VPCs and/ or AWS Accounts

  - Provision and configure cages and Stacksets seamlessly across multiple accounts

  - Use of IAM Roles to enable cross-account processes without sharing IAM credentials

*Rich Contribution Model enables Collaboration / Sharing of Workloads and Operational Building Blocks*

  - Publishers of Nucleator Stacksets provide everything that is needed for collaborators 
    to easily replicate and extend their infrastructure and process

  - Libraries of Stacksets allow users to quickly get started with diverse workloads.

*Improved Account Governance and Resource Accountability*

  - Allocation of nearly all AWS Resources to Stacksets with corresponding CloudFormation 
    Stacks makes it clear what resources exist to support which processes

  - Provides a strong accountability model and means for organizing Resources within 
    each AWS Account


Key Concepts
------------

Nucleator defines the following key concepts to allow you to create scalable, 
secure and redundant AWS architectures.

*Customer*

Nucleator can support multiple Customers in each Nucleator config. In a simple 
Nucleator installation, there may only be a single Customer, for your company. 
When using Nucleator to support managed services engagements, there may be a 
Customer for your company, and multiple additional Customers for your company's 
customers, or for your customer's customers.

In Nucleator, each Customer has a corresponding DNS domain (e.g. 47lining.com), 
through which that customer's resources can be accessed.

Nucleator can manage one or more AWS Accounts per Customer. Each Customer must 
specify at least one AWS Account.

*Cage*

A Cage is a distinct VPC, provisioned on behalf of a single customer, within which 
additional infrastructure can be deployed. A Cage in Nucleator is similar to a Cage 
in physical data center.

In Nucleator, each Cage is named based on its purpose, and is resolved via DNS as a 
subdomain of the Cage's Customer's DNS domain (e.g. build.47lining.com).

Each Cage is provisioned within exactly one of the Cage's Customer's AWS Accounts. The 
configuration for the Cage specifies the AWS Account in which the Cage should be 
provisioned.

One or more Stacksets can be provisioned within each Cage.

*AWS Account*

Nucleator can manage AWS infrastructure that is deployed across one or more AWS Accounts 
for each Customer. Allocation of infrastructure to AWS Accounts is managed at the 
granularity of a Cage. Each Cage is provisioned in exactly one AWS Account. Any Stacksets 
provisioned within that Cage will be provisioned within the same AWS Account as the Cage.

*Stackset*

A Stackset is a defined set of AWS CloudFormation Stacks whose creation, updates and deletes 
are orchestrated by Nucleator. For example, the "builder" Stackset, provisioned within the 
build Cage provides deployment environment creation and continuous integration services 
accessible via ansible.build.47lining.com, nucleator-ui.build.47lining.com and 
artifactory.build.47lining.com.

*Deployment Environment*

Some Cages act as Deployment Environments for applications within a continuous integration 
and release process. Nucleator includes out-of-the-box support for many common continuous 
integration & continuous deployment use cases. Nucleator also includes support for several 
common types of Deployment Targets, and underlying infrastructure services and deployment 
patterns that support the interactions among loosely coupled applications within a 
Deployment Environment.

*Deployment Target*

A Deployment Target is a provisioned set of services within a Deployment Environment that 
is capable of accepting Deployment Artifacts for a specific version of a specific application. 

Deployment Targets are typed, and correspond to the type of Deployment Artifact and 
infrastructure services that are required to support them.

Each Deployment Environment can include multiple Deployment Targets as required to support 
the Customer's needs.

Nucleator includes out-of-the-box support for many common types of Deployment Targets (e.g. 
Java applications served by Tomcat, Python applications, ...)


Installation
------------

You will need to have Git, Python 2.7.x and pip installed on your machine to install Nucleator.

Nucleator currently requires a modified version of Ansible. The modifications have been 
submitted to the core Ansible project but have not yet made it into the core Ansible 
repository.

To install the required Ansible version: 

> git clone --recursive --depth 1 -b nucleator_distribution https://github.com/47lining/ansible.git; cd ansible; sudo python setup.py install

Now install the core Nucleator package:

> pip install --upgrade https://github.com/47lining/nucleator-core.git

See the Nucleator Users Guide for detailed instructions on using Nucleator.


