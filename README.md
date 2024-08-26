# Calligraph: Calliope model result graphing and visualisation tool

`Calligraph` is a tool to interactively explore and visualise Calliope model results.

> [!IMPORTANT]
> Note that this is pre-release software and there are likely to bugs. Please [report issues and feedback on GitHub](https://github.com/calliope-project/calligraph)!

> [!CAUTION]
> Calligraph only works with Calliope 0.7 or higher. If you are running Calliope 0.6 or lower, use the built-in visualisation tools instead.

## Installation

`pip install calligraph`

## Use

Save a solved Calliope model to a NetCDF file with `model.to_netcdf()` or by using the appropriate settings with the Calliope command-line interface. Then run `calligraph` in the command line:

```shell
$ calligraph your_model_results.nc
```

This launches Calligraph's web interface in the default web browser on your system. To use a custom port, supply the `--port PORTNUMBER` option; if you do not want the default web browser to open, specify `-nb` or `--no-browser`.

To experiment with the built-in urban-scale model:

```python
import calliope
m = calliope.examples.urban_scale(time_subset=None)
m.run()
m.to_netcdf("urban_scale.nc")
```

Then:

```shell
$ calligraph urban_scale.nc
```
