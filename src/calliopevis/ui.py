import panel as pn
from panel.template import BootstrapTemplate

pn.extension("plotly")
pn.extension("perspective")

import calliopevis.core as core
import calliopevis.geo
import calliopevis.plot
from calliopevis.core import ModelContainer

global GLOBAL_WIDGETS


def sidebar(model_container):
    widget_carriers = pn.widgets.MultiChoice(
        name="Carriers",
        value=model_container.indices["carriers"],
        options=model_container.indices["carriers"],
    )
    widget_nodes = pn.widgets.MultiChoice(
        name="Nodes",
        value=model_container.indices["nodes"],
        options=model_container.indices["nodes"],
    )
    widget_techs = pn.widgets.MultiChoice(
        name="Techs",
        value=model_container.indices["techs_no_transmission"],
        options=model_container.indices["techs_no_transmission"],
    )
    widget_links = pn.widgets.MultiChoice(
        name="Transmission links",
        value=model_container.indices["techs_transmission"],
        options=model_container.indices["techs_transmission"],
    )
    widget_costs = pn.widgets.MultiChoice(
        name="Cost classes",
        value=model_container.indices["costs"],
        options=model_container.indices["costs"],
    )

    widgets = dict(
        carriers=widget_carriers,
        nodes=widget_nodes,
        techs=widget_techs,
        links=widget_links,
        costs=widget_costs,
    )

    btn_reset_carriers = pn.widgets.Button(
        icon="restore", name="Reset", button_type="primary"
    )
    btn_reset_nodes = pn.widgets.Button(
        icon="restore", name="Reset", button_type="primary"
    )
    btn_reset_techs = pn.widgets.Button(
        icon="restore", name="Reset", button_type="primary"
    )
    btn_reset_links = pn.widgets.Button(
        icon="restore", name="Reset", button_type="primary"
    )
    btn_reset_costs = pn.widgets.Button(
        icon="restore", name="Reset", button_type="primary"
    )
    btn_reset_carriers.on_click(lambda event: reset_filters(["carriers"]))
    btn_reset_nodes.on_click(lambda event: reset_filters(["nodes"]))
    btn_reset_techs.on_click(lambda event: reset_filters(["techs"]))
    btn_reset_links.on_click(lambda event: reset_filters(["links"]))
    btn_reset_costs.on_click(lambda event: reset_filters(["costs"]))

    def reset_filters(which):
        if "carriers" in which:
            # widget_carriers.value = [carriers[0]]
            widget_carriers.value = model_container.indices["carriers"]
        if "nodes" in which:
            widget_nodes.value = model_container.indices["nodes"]
        if "techs" in which:
            widget_techs.value = model_container.indices["techs_no_transmission"]
        if "links" in which:
            widget_links.value = model_container.indices["techs_transmission"]
        if "costs" in which:
            widget_costs.value = model_container.indices["costs"]

    # Create the sidebar
    sidebar = pn.Column(
        btn_reset_carriers,
        widget_carriers,
        btn_reset_nodes,
        widget_nodes,
        btn_reset_techs,
        widget_techs,
        btn_reset_links,
        widget_links,
        btn_reset_costs,
        widget_costs,
    )

    return sidebar, widgets


##
# Main pages
##


def page_summary(model_container):
    return pn.Column(
        "# Summary",
        pn.pane.DataFrame(core.get_model_summary_df(model_container)),
        "## Build configuration",
        pn.pane.DataFrame(core.get_build_config_df(model_container)),
        "## Solve configuration",
        pn.pane.DataFrame(core.get_solve_config_df(model_container)),
    )


def page_pernodetech(model_container):
    global GLOBAL_WIDGETS

    widget_variable_pernodetech = pn.widgets.Select(
        name="Variable",
        value="flow_cap",
        options=model_container.indices["variables_notimesteps"],
    )
    plot_pane = pn.bind(
        calliopevis.plot.fig_static,
        model_container=model_container,
        variable=widget_variable_pernodetech,
        carriers=GLOBAL_WIDGETS["carriers"],
        nodes=GLOBAL_WIDGETS["nodes"],
        techs=GLOBAL_WIDGETS["techs"],
    )
    return pn.Column(
        "# Per node/tech",
        widget_variable_pernodetech,
        pn.pane.Plotly(plot_pane, sizing_mode="stretch_both"),
    )


def page_timeseries(model_container):
    global GLOBAL_WIDGETS

    btn_time_res = pn.widgets.RadioButtonGroup(
        options=["Monthly", "Daily", "Original resolution"], value="Monthly"
    )
    widget_variable_ts = pn.widgets.Select(
        name="Variable",
        value="flow*",
        options=model_container.indices["variables_timesteps"],
    )

    plot_pane = pn.bind(
        calliopevis.plot.fig_timeseries,
        model_container=model_container,
        variable=widget_variable_ts,
        carriers=GLOBAL_WIDGETS["carriers"],
        nodes=GLOBAL_WIDGETS["nodes"],
        techs=GLOBAL_WIDGETS["techs"],
        time_res=btn_time_res,
    )

    return pn.Column(
        "# Time series",
        pn.Row("Time resolution:", btn_time_res),
        widget_variable_ts,
        pn.pane.Plotly(plot_pane, sizing_mode="stretch_both"),
    )


def page_map(model_container):
    widget_variable_map_nodes = pn.widgets.Select(
        name="Variable (nodes)",
        value="flow_cap",
        options=model_container.indices["variables_notimesteps"],
    )
    widget_variable_map_links = pn.widgets.Select(
        name="Variable (links)",
        value="flow_cap",
        options=model_container.indices["variables_notimesteps"],
    )
    plot_pane = pn.bind(
        calliopevis.geo.plot_map,
        model_container=model_container,
        node_variable=widget_variable_map_nodes,
        link_variable=widget_variable_map_links,
    )

    return pn.Column(
        "# Map", widget_variable_map_nodes, widget_variable_map_links, plot_pane
    )


def page_export(model_container):
    global GLOBAL_WIDGETS

    widget_variable_export = pn.widgets.Select(
        name="Variable",
        value="flow_cap",
        options=model_container.indices["variables"],
        # min_characters=0,
    )
    switch_dropna = pn.widgets.Switch(value=True, name="Drop N/A")

    df = pn.bind(
        core.get_generic_df,
        model_container=model_container,
        dropna=switch_dropna,
        variable=widget_variable_export,
        carriers=GLOBAL_WIDGETS["carriers"],
        nodes=GLOBAL_WIDGETS["nodes"],
        techs=GLOBAL_WIDGETS["techs"],
    )

    return pn.Column(
        "# Export data",
        pn.Row(widget_variable_export, switch_dropna),
        # pn.pane.Perspective(df, height=1000, width=1000),
        pn.pane.Perspective(df, sizing_mode="stretch_both"),
    )


##
# Navbar
##

PAGES = {
    "Summary": page_summary,
    "Per node/tech": page_pernodetech,
    "Timeseries": page_timeseries,
    "Map": page_map,
    "Export": page_export,
}

##
# Create the main area and display the first page
##

_MAIN_AREA = pn.Column()


def show_page(model_container, page):
    """Show the selected page"""
    _MAIN_AREA.clear()
    _MAIN_AREA.append(PAGES[page](model_container))


def navbar(model_container):
    # Define buttons to navigate between pages
    button_page_summary = pn.widgets.Button(name="Summary", button_type="primary")
    button_page_pernodetech = pn.widgets.Button(
        name="Per node/tech", button_type="primary"
    )
    button_page_timeseries = pn.widgets.Button(name="Timeseries", button_type="primary")
    button_page_map = pn.widgets.Button(name="Map", button_type="primary")
    button_page_export = pn.widgets.Button(
        icon="file-export", name="Export data", button_type="primary"
    )

    # Set up button click callbacks
    button_page_summary.on_click(lambda event: show_page(model_container, "Summary"))
    button_page_pernodetech.on_click(
        lambda event: show_page(model_container, "Per node/tech")
    )
    button_page_timeseries.on_click(
        lambda event: show_page(model_container, "Timeseries")
    )
    button_page_map.on_click(lambda event: show_page(model_container, "Map"))
    button_page_export.on_click(lambda event: show_page(model_container, "Export"))

    # Create the navbar
    navbar = pn.Row(
        button_page_summary,
        button_page_pernodetech,
        button_page_timeseries,
        button_page_map,
        button_page_export,
    )

    return navbar


def app(path):
    model_container = ModelContainer(path)

    global GLOBAL_WIDGETS
    sidebar_panel, GLOBAL_WIDGETS = sidebar(model_container)

    template = BootstrapTemplate(
        title="CalliopeVis",
        header=[navbar(model_container)],
        sidebar=[sidebar_panel],
        main=[_MAIN_AREA],
    )
    show_page(model_container, "Summary")
    return template
