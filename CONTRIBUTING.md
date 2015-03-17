# Contributing to Nucleator

47Lining is a strong supporter of Open Source software. We believe that open 
sourcing Nucleator is a great way to get a useful tool into the hands of users 
and maximize the potential bandwidth to make Nucleator better.

We want to keep it as easy as possible to contribute fixes / new features to 
keep the project moving forward. There are a few guidelines that we
would like contributors to follow so that we can have a chance of keeping on
top of things.

## Nucleator Core vs Stacksets

New functionality is typically focused on new stackset implementations that 
make it easy to deploy and manage sets of purpose-built AWS infrastructure.

Nucleator has a designed mechanism for defining the stacksets that are 
available to your nucleator installation. The sources.yml file in your .nucleator 
directory contains a set of git URLs that define what Nucleator stacksets are 
available to you and localized in your .nucleator/contrib directory.

This means that if you want to make a new stackset available to the Nucleator 
user community, all you have to do is publish it in a publicly-accessible 
github account. Nucleator users can simply add an entry to .nucleator/sources.yml 
pointing to your repository, run 'nucleator update' and start using your stackset.

The "Nucleator Core" is currently defined as the nucleator-core repository that 
implements the common functionality of Nucleator, along with a limited set of 
nucleator-core-* stacksets. The nucleator-core stacksets are generally focused 
on either setting up core Nucleator prerequisites in AWS or providing examples 
of how to leverage the Nucleator Core to implement common sets of infrastructure 
(Elastic Beanstalk instances, Amazon Redshift clusters, etc.),

If you are unsure of whether your contribution should be implemented as a
separate stackset or part of Nucleator Core, ask on the 
[nucleator-dev mailing list](https://groups.google.com/forum/#!forum/nucleator-dev)
for advice.

## Getting Started

* Make sure you have a [GitHub account](https://github.com/signup/free)
* Submit a ticket for your issue, assuming one does not already exist.
  * Clearly describe the issue including steps to reproduce when it is a bug.
  * Make sure you fill in the earliest version that you know has the issue.
* Fork the repository on GitHub

## Making Changes

* Create a topic branch from where you want to base your work.
  * This is usually the master branch.
  * Only target release branches if you are certain your fix must be on that
    branch.
  * To quickly create a topic branch based on master; `git checkout -b
    fix/master/my_contribution master`. Please avoid working directly on the
    `master` branch.
* Make commits of logical units.
* Check for unnecessary whitespace with `git diff --check` before committing.
* Make sure your commit messages are descriptive and include a reference to GitHub issue when appropriate.
* Be sure to test your fixes / features as completely as possible.

## Submitting Changes

* Push your changes to a topic branch in your fork of the repository.
* Submit a pull request to the appropriate repository in the 47lining organization.
* The core team looks at Pull Requests on a regular basis.
* After feedback has been given we expect responses within two weeks. After two
  weeks will may close the pull request if it isn't showing any activity.

# Licensing and IP

* Nucleator Stacksets released as separately-owned repositories may carry any 
  license the author desires, so long as that license allows invocation of the 
  stackset by the Apache 2.0-licensed Nucleator Core.

* Code and Intellectual Property contributed to Nucleator Core must be releasable 
  under the Apache 2.0 license.

# Additional Resources

* [General GitHub documentation](http://help.github.com/)
* [GitHub pull request documentation](http://help.github.com/send-pull-requests/)
