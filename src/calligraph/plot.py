import pandas as pd
import panel as pn
import plotly.express as px

from calligraph.core import get_df_static, get_df_timeseries


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


def data_timeseries(
    model_container, variable, time_res, time_range=None, sum_by="nodes", **selectors
):

    RESOLUTIONS = {"Monthly": "1ME", "Weekly": "7D", "Daily": "1D"}

    data = get_df_timeseries(
        model_container,
        variable,
        selectors=selectors,
        time_subset=time_range,
        resample=RESOLUTIONS.get(time_res, None),
        sum_by=sum_by,
    )

    return data


def fig_object_timeseries_bar(model_container, variable, data):
    return px.bar(
        data,
        x="timesteps",
        y=variable,
        color=(
            "techs"
            if "techs" in data.columns
            else "nodes" if "nodes" in data.columns else None
        ),
        color_discrete_map=model_container.colors_techs.param.values(),
    )


def fig_object_timeseries_line(model_container, variable, data):
    return px.line(
        data,
        x="timesteps",
        y=variable,
        color=(
            "techs"
            if "techs" in data.columns
            else "nodes" if "nodes" in data.columns else None
        ),
        color_discrete_map=model_container.colors_techs.param.values(),
        render_mode="webgl",
    )


def fig_object_timeseries_duration(model_container, variable, data):

    # Obtain list of columns without "timesteps" and the selected variable
    non_ts_var_cols = list(set(data.columns) - set(["timesteps", variable]))

    # A dict of all combinations of non_ts_var_col values that have some data
    combinations = (
        data.groupby(non_ts_var_cols).count().reset_index()[non_ts_var_cols].T.to_dict()
    )

    # We iterate over all combinations and query the `data` dataframe, then sort on only
    # the values of variable in that subset, before combining all the resulting sub-dataframes
    # back into a duration-sorted one
    dfs = {}
    for item in combinations.values():
        query = " and ".join(["{} == '{}'".format(k, v) for k, v in item.items()])
        ldc_data = data.query(query).sort_values(variable, ascending=False)
        ldc_data["timestep number"] = range(len(ldc_data))
        dfs[tuple(item.values())] = ldc_data
    data_sorted = pd.concat(dfs, ignore_index=True)

    return px.line(
        data_sorted,
        x="timestep number",
        y=variable,
        color=(
            "techs"
            if "techs" in data.columns
            else "nodes" if "nodes" in data.columns else None
        ),
        color_discrete_map=model_container.colors_techs.param.values(),
        render_mode="webgl",
    )


TIMESERIES_FUNCTIONS = {
    "Bar": fig_object_timeseries_bar,
    "Line": fig_object_timeseries_line,
    "Duration": fig_object_timeseries_duration,
}


def fig_timeseries(model_container, variable, plot_type, time_res, sum_by, **selectors):
    data = data_timeseries(model_container, variable, time_res, sum_by, **selectors)
    fig = TIMESERIES_FUNCTIONS[plot_type](model_container, variable, data)
    return fig


def fig_timeseries_with_subset(
    model_container, variable, plot_type, time_res, time_range, sum_by, **selectors
):
    data = data_timeseries(
        model_container, variable, time_res, time_range, sum_by, **selectors
    )
    fig = TIMESERIES_FUNCTIONS[plot_type](model_container, variable, data)
    return fig


def pane_timeseries_plot_with_slider(
    ui_view, variable, plot_type, sum_by, time_res, **selectors
):
    model_container = ui_view.model_container

    data_for_widget_init = data_timeseries(
        model_container, variable, time_res, **selectors
    )

    STEP_SIZES = {
        "Monthly": 60000 * 60 * 24 * 30,
        "Weekly": 60000 * 60 * 24 * 7,
        "Daily": 60000 * 60 * 24,
        "Original resolution": 60000 * 60,
    }

    FORMATS = {
        "Monthly": "%B %y",
        "Weekly": "%d-%m-%y",
        "Daily": "%d-%m-%y",
        "Original resolution": "%d-%m-%y %H:%M",
    }

    END_SELECTIONS = {
        "Monthly": -1,
        "Weekly": -1,
        "Daily": 30,
        "Original resolution": 60,
    }

    # For the end point of the range selector, either use the pre-defined value
    # from END_SELECTIONS or the actual available data length, whichever is smaller
    end_index = min(END_SELECTIONS[time_res], len(data_for_widget_init) - 1)

    widget_datetime_range_slider = pn.widgets.DatetimeRangeSlider(
        name="Time subset",
        start=data_for_widget_init.timesteps.iloc[0],
        end=data_for_widget_init.timesteps.iloc[-1],
        value=(
            data_for_widget_init.timesteps.iloc[0],
            data_for_widget_init.timesteps.iloc[end_index],
        ),
        step=STEP_SIZES[time_res],
        format=FORMATS[time_res],
        sizing_mode="stretch_width",
    )

    # Bind widget_datetime_range_slider to fig_object_timeseries
    fig_pane = pn.bind(
        fig_timeseries_with_subset,
        model_container=model_container,
        variable=variable,
        plot_type=plot_type,
        time_res=time_res,
        time_range=widget_datetime_range_slider,
        sum_by=sum_by.lower(),
        **selectors,
    )

    return pn.Column(
        fig_pane,  # pn.pane.Plotly(fig_pane, sizing_mode="stretch_both"),
        widget_datetime_range_slider,
    )


def pane_timeseries(ui_view, **selectors):

    btn_time_res = pn.widgets.RadioButtonGroup(
        options=["Monthly", "Weekly", "Daily", "Original resolution"], value="Monthly"
    )

    widget_variable_ts = ui_view.initialise_resettable_widget(
        id="variable_ts",
        name="Variable",
        value="flow*",
        variables="variables_timesteps",
    )

    widget_plot_type_ts = pn.widgets.RadioButtonGroup(
        options=["Bar", "Line", "Duration"], value="Bar"
    )

    btn_sumover_ts = pn.widgets.RadioButtonGroup(
        name="Sum over", options=["Nodes", "Techs"], value="Nodes"
    )

    # Bind btn_time_res to pane_timeseries_plot_with_slider
    plot_pane = pn.bind(
        pane_timeseries_plot_with_slider,
        ui_view=ui_view,
        variable=widget_variable_ts,
        plot_type=widget_plot_type_ts,
        sum_by=btn_sumover_ts,
        time_res=btn_time_res,
        **selectors,
    )

    sum_over_help_text = "Caution: if you sum over techs, you probably want to filter only some techs in the sidebar, otherwise demand and supply techs may add up to zero and you will not see anything in the plot."

    return pn.Column(
        pn.Row(widget_variable_ts, widget_plot_type_ts),
        pn.Row(
            pn.widgets.TooltipIcon(value=sum_over_help_text),
            "Sum over:",
            btn_sumover_ts,
        ),
        plot_pane,
        pn.Row("Time resolution:", btn_time_res),
    )
