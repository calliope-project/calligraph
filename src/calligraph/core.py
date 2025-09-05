import random
from pathlib import Path
from typing import Dict, List

import calliope
import pandas as pd
import param
import xarray as xr


class ResettableParam(param.Parameterized):
    def __init__(self, **params):
        super().__init__(**params)

    def _reset(self):
        for param_ in self.param:
            if param_ not in ["name", "reset"]:
                setattr(self, param_, self.param[param_].default)

    reset = param.Action(_reset, label="Reset")


class ColorPickerParam(ResettableParam):
    def __init__(self, **params):
        super().__init__(**params)
        self._pause_watching = False

    def add_color_parameter(self, name, color):
        self.param.add_parameter(name, param.Color(color))
        self.param.watch(self._update_color, [name])

    def _update_color(self, event):
        if self._pause_watching is False and self.change_same_together is True:
            self._pause_watching = True
            event_param = event.name
            prev_value = event.old
            new_value = event.new

            for param_name, param_value in self.param.values().items():
                if (
                    param_name not in self.IGNORED_PARAMS
                    and param_name != event_param
                    and prev_value == param_value
                ):
                    self.param.update(**{param_name: new_value})

            self._pause_watching = False

    IGNORED_PARAMS = ["reset", "change_same_together"]

    change_same_together = param.Boolean(False, label="Change same colors together")


class ModelContainer:
    def __init__(self, path: str | Path):
        """
        Returns a new ModelContainer from the given `path` to a Calliope NetCDF file.

        Args:
            path (str | Path)
        """
        self.model = calliope.read_netcdf(path)
        self.combined_data = xr.merge(
            [self.model.results, self.model.inputs], compat="override"
        )
        self.colors_techs = self._init_tech_colors()
        self.update_variables()

    def update_variables(self, include_inputs=True) -> None:
        """
        Updates `self.variables` with a dictionary with variable kind as keys,
        lists of variables as values.

        """
        if include_inputs:
            dataset = self.combined_data
        else:
            dataset = self.model.results

        variables = dict(
            variables=sorted(list(dataset.data_vars)),
            variables_timesteps=sorted(
                [var for var in dataset.data_vars if "timesteps" in dataset[var].dims]
                + ["flow*"]
            ),
            variables_notimesteps=sorted(
                [
                    var
                    for var in dataset.data_vars
                    if "timesteps" not in dataset[var].dims
                ]
            ),
            variables_notimesteps_nodes=sorted(
                [
                    var
                    for var in dataset.data_vars
                    if "timesteps" not in dataset[var].dims
                    and "nodes" in dataset[var].dims
                ]
            ),
            variables_notimesteps_links=sorted(
                [
                    var
                    for var in dataset.data_vars
                    if "timesteps" not in dataset[var].dims
                    and "nodes" in dataset[var].dims  # FIXME
                ]
            ),
        )
        self.variables = variables

    def _init_tech_colors(self):
        techs = self.model.results.techs.to_index().to_list()
        colors = self.model.inputs.color.to_series().to_dict()
        all_colors = {
            tech: colors.get(tech, "#" + random.randbytes(3).hex()) for tech in techs
        }
        colors_techs = ColorPickerParam()
        for k, v in all_colors.items():
            colors_techs.add_color_parameter(k, v)
        return colors_techs

    def get_base_tech_members(self, base_tech):
        return sorted(
            self.model.inputs.base_tech.where(
                self.model.inputs.base_tech.isin(base_tech), drop=True
            )
            .techs.to_index()
            .to_list()
        )

    def get_model_coords(self, ignore=["timesteps", "techs"]):
        coords = list(self.model.results.coords)
        if ignore:
            coords = set(coords) - set(ignore)
        return coords

    @property
    def name(self):
        name = str(self.model.config.init.name)
        if name == "None":
            return "Unnamed model"
        else:
            return name


def filter_selectors(
    da: xr.DataArray, selectors: Dict[str, List[str]], additional_subset: Dict = None
) -> Dict[str, List[str]]:
    for k, v in selectors.items():
        assert isinstance(v, list)

    selector_keys_to_delete = [
        k for k in selectors.keys() if k not in da.dims or selectors[k] is None
    ]
    selectors = {k: v for k, v in selectors.items() if k not in selector_keys_to_delete}

    if additional_subset:
        for k, v in additional_subset.items():
            if k in selectors:
                selectors[k] = [i for i in v if i in selectors[k]]
            else:
                selectors[k] = v

    return selectors


def _clean_df(df):
    df.columns = ["Value"]
    df.index.name = None
    return df


def get_model_summary_df(model_container):
    model = model_container.model
    results = model_container.combined_data
    data = [
        (
            "Model name",
            model.config.init.name,
        ),  # FIXME why is there also a property/method
        ("Scenario name", model.runtime.scenario),
        ("Applied overrides", model.runtime.applied_overrides),
        ("Calliope version", model.runtime.calliope_version_initialised),
        ("Technologies", len(results.techs)),
        ("Nodes", len(results.nodes)),
        ("Carriers", len(results.carriers)),
        ("Timesteps", len(results.timesteps)),
        ("Termination condition", model.runtime.termination_condition),
    ]
    df = pd.DataFrame(data).set_index(0)
    return _clean_df(df)


def get_build_config_df(model_container):
    model = model_container.model
    df = pd.Series(model.config.build.model_dump()).to_frame()
    return _clean_df(df)


def get_solve_config_df(model_container):
    model = model_container.model
    df = pd.Series(model.config.solve.model_dump()).to_frame()
    return _clean_df(df)


def get_df_static(model_container, variable, selectors):
    da = model_container.combined_data[variable]

    df_capacity = (
        da.sel(filter_selectors(da, selectors))
        .to_series()
        .where(lambda x: x != 0)
        .dropna()
        .to_frame(variable)
        .reset_index()
    )
    return df_capacity


def get_df_timeseries(
    model_container,
    variable,
    selectors,
    time_subset=None,
    resample=None,
    sum_by="nodes",
):
    results = model_container.combined_data

    if variable == "flow*":
        da = results.flow_out.fillna(0) - results.flow_in.fillna(0)
    else:
        da = results[variable]

    da_ = da.sel(filter_selectors(da, selectors))

    if resample:
        da_ = da_.resample(timesteps=resample).mean()

    if time_subset:
        da_ = da_.sel(timesteps=slice(*time_subset))

    if sum_by in da_.dims:
        da_ = da_.sum(sum_by)

    df = da_.to_series().to_frame(variable)

    return df.reset_index()


def get_generic_df(model_container, variable, dropna=False, **selectors):
    da = model_container.combined_data[variable]

    df = da.sel(filter_selectors(da, selectors)).to_dataframe()
    if dropna:
        df = df.dropna()

    return df
