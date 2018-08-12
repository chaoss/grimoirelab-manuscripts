# Instructions and description about manuscripts2

## How do I generate a report from this?

First of all, unlike the previous version of manuscripts, this version has two different data sources for GitHub data. One is `github_issues` and the other one is `github_prs`. The `github_issues` data source contains data related to both, issues and prs found in the repo. However, each item in the data source is treated as an issue i.e the items of the **pull requests** categories don't have the pull requests specific data. The `github_prs` data source, on the other hand, only has pull requests and the data related to them (`github_issues` data source will have more items than `github_prs` data source).

Note: as an example, throughout these instructions we will be enriching and analysing the [chaoss/grimoirelab-perceval](https://github.com/chaoss/grimoirelab-perceval) repository.

### Enrichment

These data sources have their own Elasticsearch indices from which they query data. This helps us separate the issues and pull requests in a GitHub repository.


- You can produce an index for the the `github_issues` data source using the following command:

```bash
$ p2o.py --enrich --index <raw_index_name> --index-enrich <enrich_index_name> -e <es_url> \
--no_inc --debug --db-host <db_host> --db-sortinghat <db_name> --db-user <db_user> \
--db-password <db_password> github <owner> <repo_name> -t <github_token>
```

Example:

```bash
$ p2o.py --enrich --index perceval_github_issues_raw --index-enrich perceval_github_issues \
-e http://localhost:9200 --no_inc --debug --db-host localhost --db-sortinghat sortinghatDB \
--db-user root github chaoss grimoirelab-perceval -t <github_token>
```

This will create a raw index by the name of `perceval_github_issues_raw` containing the issues+prs raw data from the perceval repository. The enriched data will be stored in the `perceval_github_issues` index. The `github_token` here is a token that is being used to get data using the GitHub API. [This is how you generate a token](https://blog.github.com/2013-05-16-personal-api-tokens/).


- Similarly, for a `github_prs` data source we can use this command:

```bash
$ p2o.py --enrich --index <raw_index_name> --index-enrich <enrich_index_name> -e <es_url> \
--no_inc --debug --db-host <db_host> --db-sortinghat <db_name> --db-user <db_user> \
--db-password <db_password> github <owner> <repo_name> -t <github_token> --category pull_request
```
Example:

```bash
$ p2o.py --enrich --index perceval_github_prs_raw --index-enrich perceval_github_prs \
-e http://localhost:9200 --no_inc --debug --db-host localhost --db-sortinghat sortinghatDB \
--db-user root github chaoss grimoirelab-perceval -t <github_token> --category pull_request
```

Here, the `--category pull_request` flag only queries the repo for pull requests data. This command will create a raw index by the name of `perceval_github_prs_raw` containing raw data only for pull requests, in this case from the `chaoss/grimoirelab-perceval` GitHub repo.
The enriched data will be stored in the `perceval_github_prs` index.

- The index for `git` data source has no changes and can be produced as follows:

```bash
$ p2o.py --enrich --index <raw_index_name> --index-enrich <enrich_index_name> -e <es_url> --no_inc \
--debug --db-host <db_host> --db-sortinghat <db_name> --db-user <db_user> \
--db-password <db_password> git <repository_url>
```

Example:

```bash
$ p2o.py --enrich --index perceval_git_raw --index-enrich perceval_git -e http://localhost:9200 \
--no_inc --debug --db-host localhost --db-sortinghat sortinghatDB --db-user root \
git https://github.com/chaoss/grimoirelab-perceval
```

`--db-host`, `--db-sortinghat`, `--db-user` and `--db-password` are parameters of Sortinghat.

**NOTE:** If you don't know how or what [Sortinghat](https://github.com/chaoss/grimoirelab-sortinghat) is, please [go through the tutorial](https://grimoirelab.gitbooks.io/tutorial/sortinghat/intro.html). Sortinghat helps us manage the identities of the contributors and manitainers. But in case, you don't need to know about it if you don't need identity management; which for the first try you likely won't need.

## Report Generation

This is how you can use `manuscripts2` to generate the reports:

```bash
usage: manuscripts2 [-h] [-v] [-d DATA_DIR] [-e END_DATE] [-g] [-i INTERVAL]
                    [-s START_DATE] [-u ELASTIC_URL]
                    [--data-sources [DATA_SOURCES [DATA_SOURCES ...]]]
                    [-n [NAME]] [--indices [INDICES [INDICES ...]]] [-l LOGO]

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         Show version
  -d DATA_DIR, --data-dir DATA_DIR
                        Directory to store the data results (default:
                        GENERATED-REPORT')
  -e END_DATE, --end-date END_DATE
                        End date for the report (UTC) (<) (default: now)
  -g, --debug
  -i INTERVAL, --interval INTERVAL
                        Analysis interval (month (default), quarter, year)
  -s START_DATE, --start-date START_DATE
                        Start date for the report (UTC) (>=) (default: None)
  -u ELASTIC_URL, --elastic-url ELASTIC_URL
                        Elastic URL with the enriched indexes
  --data-sources [DATA_SOURCES [DATA_SOURCES ...]]
                        Data source for the report (git, ...)
  -n [NAME], --name [NAME]
                        Report name (default: UnnamedReport)
  --indices [INDICES [INDICES ...]]
                        Indices to be used to generate the report (git_index,
                        github_index ...)
  -l LOGO, --logo LOGO  Provide a logo for the report. Allowed formats: .png,
                        .pdf, .jpg, .mps, .jpeg, .jbig2, .jb2, .PNG, .PDF,
                        .JPG, .JPEG, .JBIG2, .JB2, .eps
```

First we have to setup the module. In the root of your clone of this repository (`chaoss/grimoirelab-manuscripts`), run:

```bash
$ pip install .
```

Now, once the indices mentioned above have been created, you can run the following command to generate the report:

```bash
$ manuscripts2 -n <report_name> -d <dir_name> -s <start_date> -e <end_date> -i <time_interval> \
-u <elasticsearch_url> --data-sources <data sources to be included> \
--indices <custom_index_names> -l <custom_logo>
```

- `report_name` is the name that is to be given to the project/repository in the report. 
- `dir_name` is the name of the report directory that will be created and in which the report will exist.
- `start_date` is the start of the period in which the analysis is to be done. Format: YYYY-MM-DD.
- `end_date` is the end of the period. Format: YYYY-MM-DD.
- `time interval` is the intervals in which the data is to be gathered from. It can be a `year`, `quarter`, `month`. The default value is `month`.
- `elasticsearch_url` is the address of the elasticsearch instance where all the indices are stored.
- `data sources to be included` are the data sources using which the report is to be created. Currently we support only:
  - `git`: contains data related to all the commits made in the repository.
  - `github_issues`: contains all the tickets (issues) opened in a repository.
  - `github_prs`: contains all the reviews of code (pull requests) made on the repository.
  - We are working on adding support for more data sources (mailing lists, gerrit, gitlab and such).
- `custom_index_names`: You can provide the name of the index for a corresponding data source. By default, manuscripts resolves the indices for each of the data sources as the data source names it self. These indices are connected to the data sources in the order in which they appear. For example: if we have: **github_issues github_prs** and **git** then the indices should also follow the same order.
- `custom_logo`: This is the logo that the report will contain on its every page. By default, a Grimoirelab logo is applied to each of the pages. You can provide the path to the logo file so that that logo can be applied to the report.

On running this command, a folder will be created containing different folders for different sections of the report.

Example:

To generate the report using the above indices and `git`, `github_issues` and `github_prs` data source:

```bash
manuscripts2 -n Perceval_Project -d PERCEVAL-REPORTS -s 2016-05-01 -e 2018-04-10 -i quarter \
-u http://localhost:9200/ --data-sources git github_issues github_prs \
--indices perceval_git perceval_github_issues perceval_github_prs -l logo.png
```

Here `perceval_git`, `perceval_github_issues` and `perceval_github_prs` are the names of the indexes for `git`, `github_issues` and `github_prs` data sources respectively (created as commented above).

The generated report (a PDF file) will be, you guessed it right, a file named `report.pdf` in the `PERCEVAL-REPORTS` folder.

---

## Tests

To run the tests, first you'll have to have mysql/mariadb (10.0, 10.1) installed. This is a requirement for Sortinghat.
Then create a database by the name of `test_sh`. The temporary identities of the authors generated during tests will be stored in this data base. To create a database, you can run:

```bash
mysqladmin -u root create test_sh
```

Then, to run the tests: from inside the tests folder type:
```bash
./run_tests.py
```

You can change the level of verbosity by changing the following line in `run_tests.py`, such as:
```python
result = unittest.TextTestRunner(buffer=True, verbosity=2).run(test_suite)
```

---

## Manuscripts2: inner functionality

Manuscripts2 is supposed to be the replacement of the old manuscripts code. Manuscripts2 uses external libraries such as `elasticsearch_dsl` to query ES and uses chainable functions to calculate the metrics. This gives us an edge over the old code and helps us calculate the metrics easily.

This here, is a brief introduction to the classes and functions in Manuscripts2.

### Classes:

- Index(): This class represents an elasticsearch index. It stores the name of an elasticsearch index and the connection to elasticsearch.

- Query(): This class is used to quey data from an elasticsearch index. 

### Structure:
The main class which is being implemented is the `Query` class. `Query` provides a connection to elasticsearch, queries it and computes the response.

The important variables inside the `Query` objects are as follows:

- `search`: This is the elasticsearch_dsl Search object which is responsible of quering elasticsearch and getting the results. All the aggregations, queries and filters are applied to this Search object and then it queries elasticsearch and fetches the required results.
- `parent_agg_counter`: This is a counter counting the aggregations that are applied to the Search object. It starts with `0` and increments as aggregations are added.
- `aggregations`: This is an OrderedDict which contains all the aggregations applied. An ordered dict allows us to create nested aggregations easily, as we'll see below.
- `child_agg_counter_dict`: This dict keeps a track of the number of child aggregations that have been applied in an aggregation.

Rest of the variables are self explainatory.

##### In the derived classes file, we have two more classes:

- `PullRequests` and
- `Issues`

These are subclasses derieved from the `Query` object. They have the initial queries: `"pull_requests":"true"` and `"pull_requests":"false"` respectively. They will have class specific functions in the future as the definitions of the metrics becomes clear.


## Examples of use in Python scripts

### Example 1: Basic usage

The idea is that the user can use the chainability of functions to create nested aggs and add queries seamlessly.

```python
from manuscripts2.elasticsearch import Query, Index
github_index = Index(index="<github_index_name>")

sample = Query(github_index).add_query({"name1":"value1"})\
							.add_inverse_query({"name2":"value2"}) 
```

* github_index:
- The github_index is initialised using the Index class.
- It takes as input the name of the elasticsearch index to be used and an elasticsearch client/connection.
- If the latter is not provided, the default connection is made to `http://localhost:9200` on the local server.

* sample:
- sample is a `Query` object which has chainable functions
- `add_query`: appends query into the search variable of the Query object
- `add_inverse_query`: appends an inverse query to sthe search variable of the Query object
- This way, we can add more queries, aggregations, time periods and such to the sample object


### Example 2: Basic aggregations

Getting the number of authors who participated in the project.

```python
from manuscripts2.elasticsearch import Query, Index
github_index = Index(index="<github_index_name>")

github = Query(github_index).get_cardinality("author_uuid")
github.get_aggs()
```

Steps:

- Create an `Index` object containing the elasticsearch connection information 
- Create a `Query` object using the `Index` object created
- Add an `author_uuid` aggregation to the aggregations dict inside github object
- Get the single valued aggregation (cardinality or number of author_uuids) using the get_aggs method

Points to note:

- Aggregations similar to `get_cardinality`:
	- Numeric fields:
		- `get_sum`: get the sum of all the values of the said field (field should be numeric)
		- `get_average`: get the average of all the values of the said field (field should be numeric)
		- `get_percentile`: get the percentile of all the values of the said field (field should be numeric)
		- `get_min`: get the minimum value from all the values in the said field (field should be numeric)
		- `get_max`: get the maximum value from all the values in the said field (field should be numeric)
		- `get_extended_stats`: get the extended statistics (variance, standard deviation, and so on) for the values in the said field (field should be numeric)

	- Non Numeric:
		- `get_terms`: get term aggregation for the said field

NOTE: the `get_aggs()` function returns ony the numeric values, so in the case of `get_terms` aggregation, it will return the total count of the aggregation. It is better to use the `fetch_aggregation_results` function to get the individual terms instead.
	
There is also an `add_custom_aggregation` filter which takes in an `elasticsearch_dsl Aggregation` object as it's input and adds it to the `aggregations` dict of the object (PullRequests, Issues, Query).


### Example 3: Get all the closed issues by authors.

```python
from manuscripts2.elasticsearch import Index
from manuscripts2.elasticsearch import Issues
github_index = Index(index="<github_index_name>")  # using default es connection here

issues = Issues(github_index).is_closed()\
							 .get_cardinality("id_in_repo")\
							 .by_authors("author_name")
response = issues.fetch_aggregation_results()
```

Steps:

- Create the index object specifying the index_name to be used
- Create an Issues object with `github_index` as one of it's paremeters
- Apply the `is_closed` filter to look at closed issues
- Apply the aggregation to get cardinality (number of issues). 
- Apply the `by_authors` aggregation which becomes the parent aggregation for the `cardinality` aggregation. This step will actually pop the last added aggregation from the aggregation list (here the 'cardinality' agg) and add it as a child agg for `terms` aggregation where field is the`author_name`.
- Call the `fetch_aggregation_results` function to get the number of closed issues by authors.
- The results are stored in the `response` variable.

NOTE:

`fetch_aggregation_results` loops through all the aggregations that have been added to the Object (here: `issues`) and adds them to the Search object in the sequence in which they were added. 
Then it queries elasticsearch using the `Search().execute()` method and returns a dict of the values that it gets from elasticsearch.
This will return a response from elasticsearch in the form of a dictionary having aggregations as one of the keys. The value for that(a dict itself) will have '0' as a key with the value containing the total number of unique authors in the repo who created an issue/pr.

Points to note:

- Aggregations similar to `by_author` are:
	- `by_organizations`: It is similar to `by_authors` and is used to seggregate based on the organizations that the users belong to
	- `by_period`: This creates a `date_histogram` aggregation.


### Example 4: Moar chainability

```python
from manuscripts2.elasticsearch import Index
from manuscripts2.elasticsearch import PullRequests

github_index = Index(index="<github_index_name>")
prs = PullRequests(github_index).is_closed()\
	.get_cardinality("id_in_repo")\
	.get_cardinality("id")\
	.by_authors("author_name")\
	.by_organizations()
response = prs.fetch_aggregation_results()
```

This returns a dictionary containing the response from elasticsearch.

Here, in line 7, the caveat is that if we get cardinality on the basis of `id_in_repo`, again, then the first cardinality aggregation will be overwritten because we are storing the <aggregation_name> and <aggregation> as a key-value pair in the dict. 
We can also use a list, instead of an ordered dict, but that will hinder the functionality described in EXAMPLE 5.
We can change the dict to a list if it is decided that the below functionality is not needed.

Alternatively, we can just use the `get_aggs()` function such as:

```python

number_of_closed_prs = prs.get_cardinality("id_in_repo").get_aggs()

```
Which gives us the number of closed PRs and clears the aggregation dict for new aggregations.

What is there in the aggregations dict, though?

```python

>> prs.aggregations

OrderedDict([
		('cardinality_id_in_repo', Cardinality(field='id_in_repo', precision_threshold=3000)),
        ('terms_author_org_name', 
			Terms(aggs={0: 
        		Terms(aggs={0: 
        			Cardinality(field='id', precision_threshold=3000)}, 
        		field='author_name', missing='others', size=10000)}, 
        	field='author_org_name', missing='others', size=10000)
        	)
        ]
      )
```
As we can see, it has 2 aggregations. The first `terms` agg has a `field=author_org_name` and a child aggregation which is a `terms` aggregation with `field=author_name` which in-turn has a cardinality agg with `field=id`. The dict pops the last aggregation and adds it to the aggregation for `by_authors`, `by_organization` and `by_period`.


### Example 5: Multiple nested aggregations for the same field

```python
from manuscripts2.elasticsearch import Query, Index

commits = Index(index="<github_index_name>")

commits.get_sum("lines_changed").by_authors()
commits.get_sum("lines_added").by_authors()
commits.get_sum("lines_removed").by_authors()
commits.get_sum("files_changed").by_authors()

response = commits.fetch_aggregation_results()
```

Returns a containing aggregation of the total number of lines changed, removed, added and the total number of files changed by the authors under one aggregation. The `lines_changed`, `lines_added`, `lines_removed` and `files_changed` have aggregation ids as `0,1,2,3` respectively.

```python
commits.aggregations
	OrderedDict([('terms_author_uuid',
              Terms(aggs={0: Sum(field='lines_changed'), 
              			  1: Sum(field='lines_added'), 
              			  2: Sum(field='lines_removed'), 
              			  3: Sum(field='files_changed')}, 
              		field='author_uuid', 
              		missing='others', 
              		size=10000)
              )
	]
)
```

This allows us to get all the related aggregations in one go.


### Example 6: To get all the values from source

```python
from manuscripts2.elasticsearch import Index
from manuscripts2.elasticsearch import Issues

github_index = Index(index="<github_index_name>")
issues = Issues(github_index).is_closed()
closed_issue_age = issues.fetch_results_from_source('time_to_close_days', 'id_in_repo', dataframe=True)
print(closed_issue_age)

		  id_in_repo  time_to_close_days
	0           32                0.76
	1           50                3.19
	2           63                0.24
	3           97                2.62
	4           77               71.78
	5          108                2.54
	6          133                0.03
	7          257                0.20
	8          155                1.95
	9          358                0.80
	10         369                1.13
	11          26                0.01
	12          57                2.83
	13          80                0.07
	...			...				  ...
```
Apart from aggregations, we can ge the actual values for analysis using the `fetch_results_from_source` function.


### Example 7: To get time series data

```python
from manuscripts2.elasticsearch import Index
from manuscripts2.elasticsearch import PullRequests

github_index = Index(index="<github_index_name>")

pull_requests = PullRequests(github_index).is_closed()\
	.since(<start_date>)\
	.until(<end_date>)\
	.get_cardinality("id")\
	.by_period(period="week")
prs_by_weeks = pull_requests.get_timeseries(dataframe=True)
```
Output:
```bash
				unixtime	value
date
2015-12-28 00:00:00+00:00	1.451261e+09	1
2016-01-04 00:00:00+00:00	1.451866e+09	3
2016-01-11 00:00:00+00:00	1.452470e+09	0
2016-01-18 00:00:00+00:00	1.453075e+09	1
2016-01-25 00:00:00+00:00	1.453680e+09	0
...
```

Here, we get the number of prs closed per week since the start date until the end date.

For more examples, please look at the Sample_metrics.ipynb notebook inside the Examples folder in the main directory.


## Contributing Guidelines:

Please submit an issue if you have any doubts about the functionality or if you find a bug. You can also submit a Pull Request if you want to add some additional functionality and tag [@aswanipranjal](https://github.com/aswanipranjal) for assistance!
