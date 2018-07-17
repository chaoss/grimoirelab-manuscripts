# Readme

This folder is an initialization to the new functions and classes that have to be added to manuscripts. This file provides a brief introduction to these classes and functions.


### TODO:
- Is popping from dict and then creating the nested aggregation the most efficient way to do this?
- How do you parse 3 level nested aggregation? 
- Create a Metrics class which takes the data from the Query class, processes it and gives us an output?

### Classes:

- Index(): This class represents an elasticsearch index. It stores the name of an elasticsearch index and the connection to elasticsearch.

- Query(): This class is used to quey data from an elasticsearch index. 

### Structure:
The main Class which is being implemented is the `Query` class. `Query` provides a connection to elasticsearch, queries it and computes the response.

The important variables inside the `Query` objects are as follows:

- `search`: This is the elasticsearch_dsl Search object which is responsible of quering elasticsearch and getting the results. All the aggregations, queries and filters are applied to this Search object and then it queries elasticsearch and fetches the required results.
- `parent_agg_counter`: This is a counter counting the aggregations that are applied to the Search object. It starts with `0` and increments as aggregations are added.
- `aggregations`: This is an OrderedDict which contains all the aggregations applied. An ordered dict allows us to create nested aggregations easily, as we'll see below.
- `child_agg_counter_dict`: This dict keeps a track of the number of child aggregations that have been applied in an aggregation.

Rest of the variables are self explainatory.

#### In the derived classes file, we have two more classes:

- `PullRequests` and
- `Issues`

These are subclasses derieved from the `Query` object. They have the initial queries: `"pull_requests":"true"` and `"pull_requests":"false"` respectively. They will have class specific functions in the future as the definitions of the metrics becomes clear.


### Usage

##### EXAMPLE 1: Basic usage

The idea is that the user can use the chainability of functions to create nested aggs and add queries seamlessly.

```python
from manuscripts2.new_functions import Query, Index
github_index = Index(index="<github_index_name>")

sample = Query(github_index).add_query({"name1":"value1"})\
							.add_inverse_query({"name2":"value2"}) 
```

**github_index**:
- The github_index is initialised using the Index class.
- It takes as input the name of the elasticsearch index to be used and an elasticsearch client/connection.
- If the latter is not provided, the default connection is made to `http://localhost:9200` on the local server.

**sample**
- sample is a `Query` object which has chainable functions
- `add_query`: appends query into the search variable of the Query object
- `add_inverse_query`: appends an inverse query to sthe search variable of the Query object
- This way, we can add more queries, aggregations, time periods and such to the sample object

---

##### EXAMPLE 2: Basic aggregations- Getting the number of authors who participated in the project

```python
from manuscripts2.new_functions import Query, Index
github_index = Index(index="<github_index_name>")

github = Query(github_index).get_cardinality("author_uuid")
github.get_aggs()
```

**Steps:**

- Create an `Index` object containing the elasticsearch connection information 
- Create an `Query` object using the `Index` object created
- Add an `author_uuid` aggregation to the aggregations dict inside github object
- Get the single valued aggregation (cardinality or number of author_uuids) using the get_aggs method

**Points to Note:**

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
**NOTE:** the `get_aggs()` function returns ony the numeric values, so in the case of `get_terms` aggregation, it will return the total count of the aggregation. It is better to use the `fetch_aggregation_results` function to get the individual terms instead.
	
- There is also an `add_custom_aggregation` filter which takes in an `elasticsearch_dsl Aggregation` object as it's input and adds it to the `aggregations` dict of the object (PullRequests, Issues, Query).

---

##### EXAMPLE 3: Get all the closed issues by authors.

```python
from manuscripts2.new_functions import Index
from manuscripts2.derived_classes import Issues
github_index = Index(index="<github_index_name>")  # using default es connection here

issues = Issues(github_index).is_closed()\
							 .get_cardinality("id_in_repo")\
							 .by_authors("author_name")
response = issues.fetch_aggregation_results()
```

**Steps:**

- Create the index object specifying the index_name to be used
- Create an Issues object with `github_index` as one of it's paremeters
- Apply the `is_closed` filter to look at closed issues
- Apply the aggregation to get cardinality (number of issues). 
- Apply the `by_authors` aggregation which becomes the parent aggregation for the `cardinality` aggregation. This step will actually pop the last added aggregation from the aggregation list (here the 'cardinality' agg) and add it as a child agg for `terms` aggregation where field is the`author_name`.
- Call the `fetch_aggregation_results` function to get the number of closed issues by authors.
- The results are stored in the `response` variable.

**NOTE:**

`fetch_aggregation_results` loops through all the aggregations that have been added to the Object (here: `issues`) and adds them to the Search object in the sequence in which they were added. 
Then it queries elasticsearch using the `Search().execute()` method and returns a dict of the values that it gets from elasticsearch.
This will return a response from elasticsearch in the form of a dictionary having aggregations as one of the keys. The value for that(a dict itself) will have '0' as a key with the value containing the total number of unique authors in the repo who created an issue/pr.

**Points to Note:**

- Aggregations similar to `by_author` are:
	- `by_organizations`: It is similar to `by_authors` and is used to seggregate based on the organizations that the users belong to
	- `by_period`: This creates a `date_histogram` aggregation.

---

##### EXAMPLE 4: Moar chainability

```python
from manuscripts2.new_functions import Index
from manuscripts2.derived_classes import PullRequests

github_index = Index(index="<github_index_name>")
prs = PullRequests(github_index).is_closed()\
								.get_cardinality("id_in_repo")\
								.get_cardinality("id")\
								.by_authors("author_name")\
								.by_organizations()

response = prs.fetch_aggregation_results()
```

This returns a dictionary containing the response from elasticsearch.

Here, in line-7, the caveat is that if we get cardinality on the basis of `id_in_repo`, again, then the first cardinality aggregation will be overwritten because we are storing the <aggregation_name> and <aggregation> as a key-value pair in the dict. 
We can also use a list, instead of an ordered dict, but that will hinder the functionality described in EXAMPLE 5.
We can change the dict to a list if it is decided that the below functionality is not needed.

Alternatively, we can just use the `get_aggs()` function such as:

```python

number_of_closed_prs = prs.get_cardinality("id_in_repo").get_aggs()

```
Which gives us the number of closed PRs and clears the aggregation dict for new aggregations.

What _is_ in the aggregations dict, though?
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

---

##### EXAMPLE 5: Multiple nested aggregations for the same field:

```python
from manuscripts2.new_functions import Query, Index

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

---

##### EXAMPLE 6: To get all the values from source:

```python
from manuscripts2.new_functions import Index
from manuscripts2.derived_classes import Issues

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

---

##### EXAMPLE 7: To get time series data:

```python
from manuscripts2.new_functions import Index
from manuscripts2.derived_classes import PullRequests

github_index = Index(index="<github_index_name>")

pull_requests = PullRequests(github_index).is_closed()\
										  .since(<start_date>)\
										  .until(<end_date>)\
										  .get_cardinality("id")\
										  .by_period(period="week")

prs_by_weeks = pull_requests.get_timeseries(dataframe=True)


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

**For more examples, please look at the Sample_metrics.ipynb notebook inside the Examples folder in the main directory.**

---

### Tests:

Run tests with the command:
```python
python[3.x] -m unittest -v
```
