import collections
import random

import calliope
import pandas as pd
import xarray as xr


class ModelContainer:
    def __init__(self, path):
        self.model = m = calliope.read_netcdf(path)

        # Generates a random hex color if a dict key doesn't exist
        self.colors = collections.defaultdict(
            lambda: "#" + random.randbytes(3).hex(),
            m.inputs.color.to_series().to_dict(),
        )

        self.indices = dict(
            carriers=sorted(m.results.carriers.to_index().to_list()),
            nodes=sorted(m.results.nodes.to_index().to_list()),
            techs=sorted(m.results.techs.to_index().to_list()),
            techs_transmission=sorted(
                m.inputs.base_tech.where(
                    m.inputs.base_tech.isin("transmission"), drop=True
                )
                .techs.to_index()
                .to_list()
            ),
            techs_no_transmission=sorted(
                m.inputs.base_tech.where(
                    ~m.inputs.base_tech.isin("transmission"), drop=True
                )
                .techs.to_index()
                .to_list()
            ),
            variables=sorted(list(m.results.data_vars)),
            variables_timesteps=sorted(
                [
                    var
                    for var in m.results.data_vars
                    if "timesteps" in m.results[var].dims
                ]
                + ["flow*"]
            ),
            variables_notimesteps=sorted(
                [
                    var
                    for var in m.results.data_vars
                    if "timesteps" not in m.results[var].dims
                ]
            ),
            costs=sorted(m.results.costs.to_index().to_list()),
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
