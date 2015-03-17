#!/bin/bash

CONFLUENCE_EXPORT="$HOME/host/Downloads/NCD"
TARGET="/tmp/export"
NUCLEATOR_CORE="$HOME/git/47lining/nucleator-core"

rm -rf $TARGET
mkdir -p $TARGET
cp --archive $NUCLEATOR_CORE/documentation/site/* $TARGET/
cp --archive $CONFLUENCE_EXPORT/* $TARGET/documentation/
cd $TARGET/documentation
find -name "Nucleator-Documentation_*.html" -exec echo making '{}' a symlink to index.html \; -exec rm '{}' \; -exec ln -s index.html '{}' \;
Nucleator-Documentation_22052969.html
cd $NUCLEATOR_CORE/documentation/reference
make clean
make all
cp *.html $TARGET/documentation
sed --in-place='' 's/href="Nucleator-CLI-Reference.*\.html"/href="nucleator.html"/' $TARGET/documentation/index.html
sed --in-place='' 's/href="Quick-Start-Guide.*\.html"/href="nucleatorquickstart.html"/' $TARGET/documentation/index.html
make clean


