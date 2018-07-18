# GrimoireLab Manuscripts [![Build Status](https://travis-ci.org/chaoss/grimoirelab-manuscripts.svg?branch=master)](https://travis-ci.org/chaoss/grimoirelab-manuscripts) [![Coverage Status](https://coveralls.io/repos/github/chaoss/grimoirelab-manuscripts/badge.svg?branch=master)](https://coveralls.io/github/chaoss/grimoirelab-manuscripts?branch=master)

The aim of this project is the automatic generation of reports from the enriched indexes with items from perceval data sources (git commits, github pull requests, bugzilla bugs ...) enriched using GrimoireELK.

To follow the basic step you need the enriched indexes in the Elastic Search provided as param to the report tool.

The basic steps creating a report for git, gerrit, its and mls data sources from April 2015 to April 2017 by quarters is:

```bash

bin/manuscripts -g --data-sources git gerrit its mls -u <elastic_url> -s 2015-04-01 -e 2017-04-01 -d project_data -i quarter
```

and the PDF is generated in project_data/report.pdf_

# Usage

Use `-h` flag to show usage as follows:
```
$ > bin/manuscripts -h
-d DATA_DIR, --data-dir DATA_DIR
                        Directory to store the data results
```
**Params**:

`-d, --data-dir`: directory to store data files that will be used to create the report PDF file (csv and eps files containing metrics results).
