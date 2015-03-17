# Nucleator Project Site

The Nucleator Project Site at 47lining.github.io/nucleator
is currently constructred from three distinct sources:

1. Static pages and site css maintained in the `site` directory
2. Nucleator manpage reference materials maintained in the `reference` directory and generated via gnu make for addition to `site/documentation`
3. Nucleator User's Guide maintained in an Atlassian Confluence site and exported for addition to the `site/documentation` directory.  Apache Velocity templates used for confluence export are maintained in the `confluence` directory.

While not high-effort, the publishing process is still somewhat manual:

1. recursively copy contents of `site` to `<pubtarget>`
2. install velocity templates for confluence export in confluence server
3. export styled User's Guide, unzip and copy to `<pubtarget>/documentation`
4. make manpage reference materials and copy *.html to `<pubtarget>/documentation`
5. manually fix the link to the reference materials in `<pubtarget>/documentation/index.html` to refer to `nucleator.html`
6. copy resulting `<pubtarget>` atop a clone of the `gh-pages` branch of `47lining.github.io/nucleator`, add all, commit and push.

Steps 1-5 above are captured in a simple bash script "assemble.sh"
