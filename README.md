# Calliope View: `cview`

`cview`, pronounced "sea view", is a tool to interactively explore and visualise Calliope model results.

> [!IMPORTANT]
> Note that this is pre-release software and there are likely to bugs. Please [report issues and feedback on GitHub](https://github.com/calliope-project/cview)!

> [!CAUTION]
> `cview` only works with Calliope 0.7 or higher. If you are running Calliope 0.6 or lower, use the built-in visualisation tools instead.

## Installation

* [Install a version of Calliope >= 0.7](https://calliope.readthedocs.io/en/latest/)
* In the Python environment in which Calliope >= 0.7 is installed, run: `pip install git+https://github.com/calliope-project/cview.git#egg=cview`

## Use

Save a solved Calliope model to a NetCDF file with `model.to_netcdf()` or by using the appropriate settings with the Calliope command-line interface. Then run `cview` in the command line:

```shell
$ cview your_model_results.nc
```

This launches the `cview` web interface in the default web browser on your system. To use a custom port, supply the `--port PORTNUMBER` option; if you do not want the default web browser to open, specify `-nb` or `--no-browser`.

To experiment with the built-in urban-scale model:

```python
import calliope
m = calliope.examples.urban_scale(time_subset=None)
m.run()
m.to_netcdf("urban_scale.nc")
```

Then:

```shell
$ cview urban_scale.nc
```

## Known issues

* The page layout is inflexible and particularly suboptimal on the maps page. This will be improved once Panel 1.4.1 is available with a fix for [#6653](https://github.com/holoviz/panel/issues/6653).
* If left running for a while with no interaction, the web interface may become unresponsive and has to be refreshed manually.
* Code is badly documented and needs some cleaning up.
