import random

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


class ModelContainer:
    def __init__(self, path):
        self.model = calliope.read_netcdf(path)
        self.colors_techs = self._init_tech_colors()
        self.variables = self._init_variables()

    def _init_variables(self):
        variables = dict(
            variables=sorted(list(self.model.results.data_vars)),
            variables_timesteps=sorted(
                [
                    var
                    for var in self.model.results.data_vars
                    if "timesteps" in self.model.results[var].dims
                ]
                + ["flow*"]
            ),
            variables_notimesteps=sorted(
                [
                    var
                    for var in self.model.results.data_vars
                    if "timesteps" not in self.model.results[var].dims
                ]
            ),
        )
        return variables

    def _init_tech_colors(self):
        techs = self.model.results.techs.to_index().to_list()
        colors = self.model.inputs.color.to_series().to_dict()
        all_colors = {
            tech: colors.get(tech, "#" + random.randbytes(3).hex()) for tech in techs
        }
        colors_techs = ResettableParam()
        for k, v in all_colors.items():
            colors_techs.param.add_parameter(k, param.Color(v))
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

    def get_grouped_transmission_techs(self, grouping_param):
        groups = self.model.inputs[grouping_param]
        transmission_techs = (
            self.model.results.coords["transmission"].to_index().to_list()
        )


def clean_selector(da: xr.DataArray, carriers: list, nodes: list, techs: list) -> dict:

    selector = dict(carriers=carriers, nodes=nodes, techs=techs)

    selector_keys_to_delete = [
        k for k in selector.keys() if k not in da.dims or selector[k] is None
    ]
    for k in selector_keys_to_delete:
        del selector[k]

    return selector


def get_model_summary_df(model_container):
    results = model_container.model.results
    data = [
        ("Model name", results.attrs["name"]),
        ("Scenario name", results.attrs["scenario"]),
        ("Applied overrides", results.attrs["applied_overrides"]),
        ("Calliope version", results.attrs["calliope_version_initialised"]),
        ("Technologies", len(results.techs)),
        ("Nodes", len(results.nodes)),
        ("Carriers", len(results.carriers)),
        ("Timesteps", len(results.timesteps)),
        ("Applied additional math", results.attrs["applied_additional_math"]),
        ("Termination condition", results.attrs["termination_condition"]),
    ]
    return pd.DataFrame(data, columns=["Property", "Value"]).set_index("Property")


def get_build_config_df(model_container):
    results = model_container.model.results
    return pd.DataFrame.from_dict(results.attrs["config"]["build"], orient="index")[0]


def get_solve_config_df(model_container):
    results = model_container.model.results
    return pd.DataFrame.from_dict(results.attrs["config"]["solve"], orient="index")[0]


def get_df_static(model_container, variable, carriers=None, nodes=None, techs=None):
    # da = model.results.flow_cap.where(
    #         ~model.inputs.base_tech.str.contains("demand|transmission")
    #     )

    da = model_container.model.results[variable]

    selector = clean_selector(da, carriers, nodes, techs)

    df_capacity = (
        da.sel(selector)
        .to_series()
        .where(lambda x: x != 0)
        .dropna()
        .to_frame(variable)
        .reset_index()
    )
    return df_capacity


def get_df_timeseries(
    model_container, variable, carriers=None, nodes=None, techs=None, resample=None
):
    results = model_container.model.results

    if variable == "flow*":
        da = results.flow_out.fillna(0) - results.flow_in.fillna(0)
    else:
        da = results[variable]

    selector = clean_selector(da, carriers, nodes, techs)

    df = (
        da.sel(selector)
        .sum("nodes")
        .to_series()
        .where(lambda x: x != 0)
        .dropna()
        .to_frame(variable)
    )
    if resample is not None:
        # df = df.groupby([pd.Grouper(level='techs'),
        #     pd.Grouper(level='carriers'),
        #     pd.Grouper(level='timesteps', freq=resample)]
        #   ).mean()
        df = df.groupby(
            [pd.Grouper(level=i) for i in df.index.names if i != "timesteps"]
            + [pd.Grouper(level="timesteps", freq=resample)]
        ).mean()

    # df_electricity_demand = df_electricity[df_electricity.techs == "demand_electricity"]
    # df_electricity_other = df_electricity[df_electricity.techs != "demand_electricity"]
    return df.reset_index()


def get_generic_df(
    model_container, variable, dropna=False, carriers=None, nodes=None, techs=None
):

    da = model_container.model.results[variable]

    selector = clean_selector(da, carriers, nodes, techs)

    df = da.sel(selector).to_dataframe()
    if dropna:
        df = df.dropna()

    return df
