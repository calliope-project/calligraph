from typing import Callable, Literal

import calliope
import pandas as pd
import panel as pn
import xyzservices.providers as xyz
from bokeh.models import ColumnDataSource, HoverTool, TapTool
from bokeh.plotting import figure
from pyproj import Transformer

from calligraph.core import filter_selectors

# Transform from Web Mercator to Lat/Lon
# `always_xy` ensures that the order of the resulting tuple remains (horizontal axis, vertical axis), irrespective of the CRS.
LONLAT_TO_MERCATOR = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)


def get_geo_bounds(model: calliope.Model, as_mercator=False, padding=0.1):
    df = get_nodes_geo(model, as_mercator=False)
    bounds = df.loc[:, ["longitude", "latitude"]].describe().loc[["min", "max"], :].T
    if padding:
        padding_absolute = (bounds["max"] - bounds["min"]).max() * padding
        bounds["min"] -= padding_absolute
        bounds["max"] += padding_absolute
    if as_mercator:
        return bounds.apply(_to_mercator)
    else:
        return bounds


def get_nodes_geo(model, as_mercator=False, selectors=None):
    nodes = model.inputs[["nodes", "longitude", "latitude"]]

    if selectors:
        nodes = nodes.sel(filter_selectors(nodes, selectors))

    nodes = nodes.to_dataframe()
    if as_mercator:
        updated = nodes.apply(_to_mercator, axis=1)
        return updated
    else:
        return nodes


def get_line_xs_ys(model, as_mercator: bool = False, selectors: dict | None = None):
    da = model.inputs.sel(**selectors) if selectors is not None else model.inputs
    links = (
        da.sel(**selectors)[["longitude", "latitude"]]
        .where(da.definition_matrix & da.base_tech.isin("transmission"))
        .to_dataframe()
        .droplevel("carriers")
        .dropna()
    )
    if as_mercator:
        links = links.apply(_to_mercator, axis=1)
    grouped_links = links.groupby("techs", group_keys=False).apply(
        lambda x: pd.Series(
            {
                "xs": x.longitude.to_list(),
                "ys": x.latitude.to_list(),
                "node_from": x.index.get_level_values("nodes")[0],
                "node_to": x.index.get_level_values("nodes")[1],
            }
        )
    )

    return grouped_links


def _to_mercator(row: pd.Series) -> pd.Series:
    transformed = LONLAT_TO_MERCATOR.transform(row["longitude"], row["latitude"])
    return pd.Series(data=transformed, index=["longitude", "latitude"])


def get_geo_data(
    model: calliope.Model,
    techs: list[str],
    variable: str,
    selectors: dict[str, list[str]],
    unstack_dim: Literal["nodes", "techs"],
    concat_func: Callable,
) -> pd.DataFrame:
    da = (
        model.results[variable] if variable in model.results else model.inputs[variable]
    )
    df = (
        da.sel(filter_selectors(da, selectors, additional_subset={"techs": techs}))
        .to_series()
        .unstack(unstack_dim)
    )
    html_strings = df.apply(lambda row: row.dropna().to_frame(variable).to_html())
    df.index = df.index.map("{0[0]}__{0[1]}".format)
    df = pd.concat(
        [
            concat_func(model, as_mercator=True, selectors=selectors),
            df.T,
            html_strings.to_frame("html"),
        ],
        axis=1,
    )
    if unstack_dim == "techs":
        df["color"] = model.inputs.color.sel(techs=techs)
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
        self.df_nodes = get_geo_data(
            model,
            techs_no_transmission,
            node_variable,
            selectors,
            "nodes",
            get_nodes_geo,
        )
        self.df_links = get_geo_data(
            model, techs_transmission, link_variable, selectors, "techs", get_line_xs_ys
        )
        src_nodes = ColumnDataSource(self.df_nodes)
        src_links = ColumnDataSource(self.df_links)

        tooltips_nodes = "<div>@html</div>"
        tooltips_links = "<div>@node_from → @node_to</div><div>@html</div>"

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
