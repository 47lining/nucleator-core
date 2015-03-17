# Nucleator Reference Documentation

In order to be able to add the documentation in various formats (doc, html, info), these additional dependencies are required:

RedHat variants:

```
$ yum install asciidoc xmlto docbook2x source-highlight
```

Debian variants:

```
$ apt-get install asciidoc xmlto docbook2x source-highlight
```

If you use MacPorts, you can 'port install' the same packages.

To make the documentation:

```
cd documentation
make clean
make all
```
