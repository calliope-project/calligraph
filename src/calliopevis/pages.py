import panel as pn

import calliopevis.core as core
import calliopevis.geo
import calliopevis.plot

HOME_WARNING = """### Warning: Pre-release software

This is alpha/pre-release software. It is likely to break in unexpected ways! Please report issues and bugs."""


def page_home(ui_view):
    model_container = ui_view.model_container
    return pn.Column(
        pn.pane.Alert(HOME_WARNING, alert_type="warning"),
        pn.Row(
            pn.Column(
                pn.pane.DataFrame(core.get_model_summary_df(model_container)),
                "## Build configuration",
                pn.pane.DataFrame(core.get_build_config_df(model_container)),
                "## Solve configuration",
                pn.pane.DataFrame(core.get_solve_config_df(model_container)),
            ),
            pn.Column(pn.Param(model_container.colors_techs, name="Tech colors")),
        ),
    )


def page_pernodetech(ui_view):
    model_container = ui_view.model_container
    widget_variable_pernodetech = pn.widgets.Select(
        name="Variable",
        value="flow_cap",
        options=model_container.variables["variables_notimesteps"],
    )
    plot_pane = pn.bind(
        calliopevis.plot.fig_static,
        model_container=model_container,
        variable=widget_variable_pernodetech,
        carriers=ui_view.coord_selectors["carriers"],
        nodes=ui_view.coord_selectors["nodes"],
        techs=ui_view.coord_selectors["techs"],
    )
    return pn.Column(
        widget_variable_pernodetech,
        pn.pane.Plotly(plot_pane, sizing_mode="stretch_both"),
    )


def page_timeseries(ui_view):
    model_container = ui_view.model_container
    btn_time_res = pn.widgets.RadioButtonGroup(
        options=["Monthly", "Daily", "Original resolution"], value="Monthly"
    )
    widget_variable_ts = pn.widgets.Select(
        name="Variable",
        value="flow*",
        options=model_container.variables["variables_timesteps"],
    )

    plot_pane = pn.bind(
        calliopevis.plot.fig_timeseries,
        model_container=model_container,
        variable=widget_variable_ts,
        carriers=ui_view.coord_selectors["carriers"],
        nodes=ui_view.coord_selectors["nodes"],
        techs=ui_view.coord_selectors["techs"],
        time_res=btn_time_res,
    )

    return pn.Column(
        pn.Row("Time resolution:", btn_time_res),
        widget_variable_ts,
        pn.pane.Plotly(plot_pane, sizing_mode="stretch_both"),
    )


def page_map(ui_view):
    model_container = ui_view.model_container
    widget_variable_map_nodes = pn.widgets.Select(
        name="Variable (nodes)",
        value="flow_cap",
        options=model_container.variables["variables_notimesteps"],
    )
    widget_variable_map_links = pn.widgets.Select(
        name="Variable (links)",
        value="flow_cap",
        options=model_container.variables["variables_notimesteps"],
    )
    sel_map_tech = pn.widgets.Select(
        name="Tech to show", value="", options=ui_view.coord_selectors["techs"].value
    )
    plot_pane = pn.bind(
        calliopevis.geo.plot_map,
        ui_view=ui_view,
        node_variable=widget_variable_map_nodes,
        link_variable=widget_variable_map_links,
    )

    return pn.Column(
        widget_variable_map_nodes, widget_variable_map_links, sel_map_tech, plot_pane
    )


def page_table(ui_view):
    model_container = ui_view.model_container
    widget_variable_export = pn.widgets.Select(
        name="Variable",
        value="flow_cap",
        options=model_container.variables["variables"],
    )
    switch_dropna = pn.widgets.Switch(value=True, name="Drop N/A")

    df = pn.bind(
        core.get_generic_df,
        model_container=model_container,
        dropna=switch_dropna,
        variable=widget_variable_export,
        carriers=ui_view.coord_selectors["carriers"],
        nodes=ui_view.coord_selectors["nodes"],
        techs=ui_view.coord_selectors["techs"],
    )

    return pn.Column(
        pn.Row(widget_variable_export, switch_dropna),
        pn.pane.Perspective(df, sizing_mode="stretch_both"),
    )
