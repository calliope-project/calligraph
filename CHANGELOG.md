## 0.1.1.dev7

* Compatibility with calliope 0.7.0.dev7

## 0.1.1.dev5

* Compatibility with calliope 0.7.0.dev6

## 0.1.1.dev4 (2024-11-22)

* Fix converting config options to dataframe when there are nested dictionaries in the config (e.g. `solve.solver_options`).
* CLI: default to random port, making it easier to run several instances in parallel

## 0.1.1.dev2

* Minor bug fixes: 0 values in timeseries may be dropped; summing should only happen when dim exists

## 0.1.1.dev1 (2024-10-18)

* "Line" and "Duration" time series plot types
* Time series plots can sum by nodes or techs
* Time series plots don't break on models with only few timesteps
* Support models without a name

## 0.1.1.dev0 (2024-08-26)

* Name changed to **Calligraph**
* Time series subsetting (#1)
* Improved time series plotting on map page
* Zoom maps by zoom wheel (#5)
* Permit changing the same colors together
* Various bug fixes and improvements

## 0.1.0 (2024-04-04)

Initial release
