import calliope
import pandas as pd
import panel as pn
import xyzservices.providers as xyz
from bokeh.models import ColumnDataSource, HoverTool, TapTool
from bokeh.plotting import figure
from pyproj import Transformer

from calligraph.core import filter_selectors

# Transform from Web Mercator to Lat/Lon
MERCATOR_TO_LATLON = Transformer.from_crs("EPSG:3857", "EPSG:4326")
LATLON_TO_MERCATOR = Transformer.from_crs("EPSG:4326", "EPSG:3857")


def get_geo_bounds(model: calliope.Model, as_mercator=False, padding=0.1):
    df = get_nodes_geo(model, as_mercator=False)
    bounds = df.loc[:, ["longitude", "latitude"]].describe().loc[["min", "max"], :].T
    if padding:
        padding_absolute = (bounds["max"] - bounds["min"]).max() * padding
        bounds["min"] -= padding_absolute
        bounds["max"] += padding_absolute
    if as_mercator:
        return bounds.apply(
            lambda x: LATLON_TO_MERCATOR.transform(x["latitude"], x["longitude"])
        )
    else:
        return bounds


def get_nodes_geo(model, as_mercator=False, selectors=None):
    nodes = model._model_data[["nodes", "longitude", "latitude"]]

    if selectors:
        nodes = nodes.sel(filter_selectors(nodes, selectors))

    nodes = nodes.to_dataframe()
    if as_mercator:
        return nodes.apply(
            lambda x: LATLON_TO_MERCATOR.transform(x["latitude"], x["longitude"]),
            axis=1,
            result_type="broadcast",
        )
    else:
        return nodes


def get_links_geo(model, nodes, selectors=None):
    df = pd.DataFrame(
        {
            k: {"node_from": v["from"], "node_to": v["to"]}
            for k, v in model._model_def_dict["techs"].items()
            if "from" in v and v["from"] in nodes.index and v["to"] in nodes.index
        }
    ).T
    if selectors is not None and "techs" in selectors:
        df = df.loc[[i for i in selectors["techs"] if i in df.index], :]
    return df


def get_line_xs_ys(model, as_mercator=False, selectors=None):
    nodes = get_nodes_geo(model, as_mercator=as_mercator, selectors=selectors)
    links = get_links_geo(model, nodes=nodes, selectors=selectors)

    if len(links) > 0:
        for link in links.index:
            node_from = links.loc[link, "node_from"]
            node_to = links.loc[link, "node_to"]
            links.loc[link, "lon_from"], links.loc[link, "lon_to"] = (
                nodes.loc[node_from, "longitude"],
                nodes.loc[node_to, "longitude"],
            )
            links.loc[link, "lat_from"], links.loc[link, "lat_to"] = (
                nodes.loc[node_from, "latitude"],
                nodes.loc[node_to, "latitude"],
            )

        links["xs"] = links.apply(lambda x: x[["lon_from", "lon_to"]].to_list(), axis=1)
        links["ys"] = links.apply(lambda x: x[["lat_from", "lat_to"]].to_list(), axis=1)

    return links


def get_geo_node_data(model, techs, variable, selectors):
    da = model._model_data[variable]
    df = da.sel(
        filter_selectors(da, selectors, additional_subset={"techs": techs})
    ).to_dataframe()
    columns = list(df.index.names)
    columns.remove("nodes")
    df = df.pivot_table(index="nodes", columns=columns)
    df[*["html"] * len(df.columns.names)] = df.apply(
        lambda row: row.dropna().to_frame().to_html(), axis=1
    )
    df.columns = df.T.index.droplevel().to_flat_index()
    df.columns = ["__".join(i) for i in df.columns]
    df = get_nodes_geo(model, as_mercator=True, selectors=selectors).join(df)
    return df


def get_geo_link_data(model, techs, variable, selectors):
    da = model._model_data[variable]
    df = da.sel(
        filter_selectors(da, selectors, additional_subset={"techs": techs})
    ).to_dataframe()
    columns = list(df.index.names)
    columns.remove("techs")

    df = df.pivot_table(index="techs", columns=columns)
    df[*["html"] * len(df.columns.names)] = df.apply(
        lambda row: row.dropna().to_frame().to_html(), axis=1
    )
    df.columns = df.T.index.droplevel().to_flat_index()
    df.columns = ["__".join(i) for i in df.columns]

    df = get_line_xs_ys(model, as_mercator=True, selectors=selectors).join(df)

    df["color"] = model.inputs.color.sel(techs=df.index)

    return df


class MapPlot:
    def __init__(self, ui_view):
        self.ui_view = ui_view
        self.df_nodes = None
        self.df_links = None
        self.selected_nodes = pn.widgets.MultiChoice(
            value=ui_view.coord_selectors["nodes"].value,
            options=ui_view.coord_selectors["nodes"].value,
        )
        self.bounds = get_geo_bounds(ui_view.model_container.model, as_mercator=True)

    def nodes_indices_change(self, attr, old, new):
        if len(new) > 0:
            self.selected_nodes.value = self.df_nodes.iloc[new].index.to_list()
        else:
            self.selected_nodes.value = self.ui_view.coord_selectors["nodes"].value

    def plot(self, ui_view, node_variable, link_variable, **selectors):
        model = ui_view.model_container.model
        techs_no_transmission = [
            i
            for i in ui_view.coord_selectors["techs"].value
            if ui_view.model_container.model.inputs.base_tech.loc[i].data
            != "transmission"
        ]
        techs_transmission = [
            i
            for i in ui_view.coord_selectors["techs"].value
            if ui_view.model_container.model.inputs.base_tech.loc[i].data
            == "transmission"
        ]
        self.df_nodes = get_geo_node_data(
            model, techs_no_transmission, node_variable, selectors
        )
        self.df_links = get_geo_link_data(
            model, techs_transmission, link_variable, selectors
        )

        src_nodes = ColumnDataSource(self.df_nodes)
        src_links = ColumnDataSource(self.df_links)

        tooltips_nodes = "<div>@html__html</div>"
        tooltips_links = "<div>@node_from → @node_to</div><div>@html__html</div>"

        # Range bounds must be supplied in web mercator coordinates
        p = figure(
            x_range=self.bounds.loc["longitude", :].to_list(),
            y_range=self.bounds.loc["latitude", :].to_list(),
            x_axis_type="mercator",
            y_axis_type="mercator",
            sizing_mode="scale_both",
            tools="pan,wheel_zoom,box_zoom,reset",
            active_scroll="wheel_zoom",
        )

        p.add_tile(xyz.Stadia.StamenTonerLite, retina=True)

        p1 = p.scatter(
            x="longitude",
            y="latitude",
            size=15,
            fill_color="#0072b5",
            line_color="#0072b5",
            fill_alpha=0.8,
            source=src_nodes,
        )
        p.add_tools(
            HoverTool(
                renderers=[p1],
                tooltips=tooltips_nodes,
                visible=True,
                description="Hover info on nodes",
            )
        )
        p.add_tools(TapTool(renderers=[p1]))
        src_nodes.selected.on_change("indices", self.nodes_indices_change)

        p2 = p.multi_line(
            xs="xs",
            ys="ys",
            line_width=3,
            line_color="color",
            line_alpha=0.8,
            hover_line_color="color",
            hover_line_alpha=0.5,
            source=src_links,
        )
        p.add_tools(
            HoverTool(
                renderers=[p2],
                tooltips=tooltips_links,
                visible=True,
                description="Hover info on links",
            )
        )

        return p
