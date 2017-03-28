# GrimoireLab Reports

The aim of this project is the automatic generation of reports from the enriched indexes with items from perceval data sources (git commits, github pull requests, bugzilla bugs ...) enriched using GrimoireELK.

In order to generate a report you need to generate first the data and figures and then to create the PDF report with this data using a LaTeX template.

Right now this document is still incomplete but you can contact us if you want to start using this project: _info@bitergia.com_.

To follow the basic step you need the enriched indexes in the Elastic Search provided as param to the report tool.

The basic steps are for including in the report gerrit metrics but not ticketing (its) metrics, from April 2015 to April 2017 by quarters, is:

```bash
cd report
./report.py -g -c report-gerrit-no-its.cfg -u <elastic_url> -s 2015-04-01 -e 2017-04-01 -d project_data -i quarter
```
Once you have the data and figures in report/project_data let's use this information for generating the PDF report.

```bash
cd report_template/
ln -s ../report/project_data data
ln -s ../report/project_data figs
make
```

and the PDF is generated in _pdf/report.pdf_
