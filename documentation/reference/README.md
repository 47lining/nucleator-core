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

N.B. Run the two make steps separately. "make clean all" has issues since it seems to start the all
in parallel with the clean and the required cmds-core.txt is not present.

```
    ASCIIDOC nucleator.html
asciidoc: WARNING: nucleator.txt: line 62: include file not found: /Users/mchance/Projects/47Lining/Nucleator/src/nucleator-core/documentation/reference/cmds-core.txt
```

So the cmds-core.txt must be made after a clean:

```
make all
    GEN cmd-list.made
cmds-core.txt
    GEN doc.dep
    ASCIIDOC nucleator.html
    ASCIIDOC nucleator.xml
    XMLTO nucleator.1
    ASCIIDOC nucleatorquickstart.xml
    XMLTO nucleatorquickstart.7
```

Or:

```
make clean cmd-list.made
make html
    ASCIIDOC nucleator-account-rolespec.html
asciidoc: WARNING: missing theme: cli
```

To avoid the theme warning:

```
cp ../site/css/cli.css ~/.asciidoc/themes/cli
```
