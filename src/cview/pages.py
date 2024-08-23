import panel as pn

import cview.core as core
import cview.geo
import cview.plot


def page_home(ui_view):
    model_container = ui_view.model_container
    return pn.Column(
        pn.Row(
            pn.Column(
                pn.pane.DataFrame(core.get_model_summary_df(model_container)),
                "## Build configuration",
                pn.pane.DataFrame(core.get_build_config_df(model_container)),
                "## Solve configuration",
                pn.pane.DataFrame(core.get_solve_config_df(model_container)),
            ),
            pn.Column(pn.Param(model_container.colors_techs, name="Tech colors")),
        )
    )


def page_pernodetech(ui_view):
    model_container = ui_view.model_container
    widget_variable_pernodetech = ui_view.initialise_resettable_widget(
        id="variable_pernodetech",
        name="Variable",
        value="flow_cap",
        variables="variables_notimesteps",
    )
    plot_pane = pn.bind(
        cview.plot.fig_static,
        model_container=model_container,
        variable=widget_variable_pernodetech,
        **{i: ui_view.coord_selectors[i] for i in ui_view.filter_coords},
    )
    return pn.Column(
        widget_variable_pernodetech,
        pn.pane.Plotly(plot_pane, sizing_mode="stretch_both"),
    )


def page_timeseries(ui_view):
    return cview.plot.pane_timeseries(ui_view)


def page_map(ui_view):
    model_container = ui_view.model_container
    widget_variable_map_nodes = ui_view.initialise_resettable_widget(
        id="variable_map_nodes",
        name="Variable (nodes)",
        value="flow_cap",
        variables="variables_notimesteps_nodes",
    )
    widget_variable_map_links = ui_view.initialise_resettable_widget(
        id="variable_map_links",
        name="Variable (links)",
        value="flow_cap",
        variables="variables_notimesteps_links",
    )

    map_plot = cview.geo.MapPlot(ui_view)

    plot_pane = pn.bind(
        map_plot.plot,
        ui_view=ui_view,
        node_variable=widget_variable_map_nodes,
        link_variable=widget_variable_map_links,
        **{i: ui_view.coord_selectors[i] for i in ui_view.filter_coords},
    )

    btn_time_res = pn.widgets.RadioButtonGroup(
        options=["Monthly", "Daily", "Original resolution"], value="Monthly"
    )

    plot_timeseries_pane = pn.bind(
        cview.plot.fig_timeseries,
        model_container=model_container,
        variable="flow_out",  # FIXME: selector for timeseries variables
        time_res=btn_time_res,
        **{
            i: ui_view.coord_selectors[i] for i in ui_view.filter_coords if i != "nodes"
        },
        nodes=map_plot.selected_nodes,
    )

    plot_static_pane = pn.bind(
        cview.plot.fig_static,
        model_container=model_container,
        variable=widget_variable_map_nodes,
        **{
            i: ui_view.coord_selectors[i] for i in ui_view.filter_coords if i != "nodes"
        },
        nodes=map_plot.selected_nodes,
    )

    map_side_plots = pn.Column(btn_time_res, plot_timeseries_pane, plot_static_pane)

    return [
        pn.Column(widget_variable_map_nodes, widget_variable_map_links, plot_pane),
        pn.Column(map_side_plots),
    ]


def page_table(ui_view):
    model_container = ui_view.model_container

    widget_variable_export = ui_view.initialise_resettable_widget(
        id="variable_export", name="Variable", value="flow_cap", variables="variables"
    )

    switch_dropna = pn.widgets.Switch(value=True, name="Drop N/A")

    df = pn.bind(
        core.get_generic_df,
        model_container=model_container,
        dropna=switch_dropna,
        variable=widget_variable_export,
        **{i: ui_view.coord_selectors[i] for i in ui_view.filter_coords},
    )

    return pn.Column(
        pn.Row(widget_variable_export, "Drop N/A values?", switch_dropna),
        pn.pane.Perspective(df, sizing_mode="stretch_both"),
    )
