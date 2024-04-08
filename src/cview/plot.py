import plotly.express as px

from cview.core import get_df_static, get_df_timeseries


def fig_static(model_container, variable, **selectors):
    data = get_df_static(model_container, variable, selectors)

    fig = px.bar(
        data,
        x=(
            "nodes"
            if "nodes" in data.columns
            else "techs" if "techs" in data.columns else "costs"
        ),
        y=variable,
        color="techs" if "techs" in data.columns else None,
        facet_col="carriers" if "carriers" in data.columns else None,
        color_discrete_map=model_container.colors_techs.param.values(),
    )
    return fig


def fig_timeseries(model_container, variable, time_res, **selectors):

    RESOLUTIONS = {"Monthly": "1M", "Daily": "1D"}

    data = get_df_timeseries(
        model_container,
        variable,
        selectors=selectors,
        resample=RESOLUTIONS.get(time_res, None),
    )

    fig = px.bar(
        data,
        x="timesteps",
        y=variable,
        color="techs" if "techs" in data.columns else None,
        color_discrete_map=model_container.colors_techs.param.values(),
    )

    # fig.add_scatter(
    #     x=df_electricity_demand.timesteps,
    #     y=-1 * df_electricity_demand["Flow in/out (kWh)"],
    #     marker_color="black",
    #     name="demand",
    # )

    return fig
