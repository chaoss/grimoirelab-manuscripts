For generating the report data for a project since 2015:

    ./report.py -e <elastic_url> -s 2015-01-01

Filters can also be used. To filter bots and merge commits:

    ./report.py -e <elastic_url> -s 2015-01-01 -f *files:0 *bot:1
