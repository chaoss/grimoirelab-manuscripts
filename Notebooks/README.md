# Readme

This folder contains the notebooks which analyse [GMD metrics](https://github.com/chaoss/wg-gmd/blob/master/2_Growth-Maturity-Decline.md).

The directory structure is as follows:

- GMD-manuscripts2.ipynb
- Plotly
	- Plotly.ipynb: This notebook contains some of the GMD metrics that are being analysed using the Plotly visualization library
- Altair
	- Altair1.ipynb: This notebook looks at the visualisations that can be added for the GMD metrics. Not all Metrics are being visualised here.
	- Altair2.ipynb: This notebook tries to look at whole projects(containing multiple repositories) and visualises the number of commits made per author over a preiod of time.
	- html: HTML pages corresponding to the visualisations in the Altair2.ipynb notebook.
	- images: Images of the visualisations from Altair1.ipynb
	- pdfs: The visualisations converted to PDFs.

### Setup:
To setup the environment for these notebooks, first you would have to [setup Jupyter Notebooks](http://jupyter.org/install) on your system.

After that, you should run:
```bash
$ pip install -r requirements.txt
```

This command should help you install the necessary libraries.

Then from inside this folder, run:
```bash
jupyter notebook
```
which should open a new window (or a tab) running Jupyter on your browser. The details of what each of the notebook does is inside the notebook it self.

**Note:** These notebooks are for hands-on analyses and experimenting whti the metrics. We are working on adding the functionality to create PDF reports for the GMD metrics. 