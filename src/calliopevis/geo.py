import calliope
import pandas as pd
import xyzservices.providers as xyz
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.plotting import figure
from pyproj import Transformer

# Transform from Web Mercator to Lat/Lon
MERCATOR_TO_LATLON = Transformer.from_crs("EPSG:3857", "EPSG:4326")
LATLON_TO_MERCATOR = Transformer.from_crs("EPSG:4326", "EPSG:3857")


def get_geo_bounds(model: calliope.Model, as_mercator=False, padding=0):
    df = get_nodes_geo(model, as_mercator=False)
    bounds = df.loc[:, ["longitude", "latitude"]].describe().loc[["min", "max"], :].T
    if padding:
        bounds["min"] -= padding
        bounds["max"] += padding
    if as_mercator:
        return bounds.apply(
            lambda x: LATLON_TO_MERCATOR.transform(x["latitude"], x["longitude"])
        )
    else:
        return bounds


def get_nodes_geo(model, as_mercator=False):
    nodes = model._model_data[["nodes", "longitude", "latitude"]].to_dataframe()
    if as_mercator:
        return nodes.apply(
            lambda x: LATLON_TO_MERCATOR.transform(x["latitude"], x["longitude"]),
            axis=1,
            result_type="broadcast",
        )
    else:
        return nodes


def get_links_geo(model):
    df = pd.DataFrame(
        {
            k: {"node_from": v["from"], "node_to": v["to"]}
            for k, v in model._model_def_dict["techs"].items()
            if "from" in v
        }
    ).T
    return df


def get_line_xs_ys(model, as_mercator=False):
    nodes = get_nodes_geo(model, as_mercator=as_mercator)
    links = get_links_geo(model)
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


def get_geo_node_data(model, techs, variable):
    df = model.results[variable].sel(techs=techs).to_dataframe()
    columns = list(df.index.names)
    columns.remove("nodes")
    df = df.pivot_table(index="nodes", columns=columns)
    df.columns = df.T.index.droplevel().to_flat_index()
    df.columns = ["__".join(i) for i in df.columns]
    df = get_nodes_geo(model, as_mercator=True).join(df)
    return df


def get_geo_link_data(model, techs, variable):
    df = model.results[variable].sel(techs=techs).to_dataframe()
    columns = list(df.index.names)
    columns.remove("techs")

    df = df.pivot_table(index="techs", columns=columns)

    df = df.apply(
        lambda x: x.dropna().to_string().strip("nodes carriers"), axis=1
    ).to_frame("data")

    df = get_line_xs_ys(model, as_mercator=True).join(df)
    return df


def plot_map(ui_view, node_variable, link_variable):
    model = ui_view.model_container.model
    techs_no_transmission = [
        i
        for i in ui_view.coord_selectors["techs"].value
        if ui_view.model_container.model.inputs.base_tech.loc[i].data != "transmission"
    ]
    techs_transmission = [
        i
        for i in ui_view.coord_selectors["techs"].value
        if ui_view.model_container.model.inputs.base_tech.loc[i].data == "transmission"
    ]
    df_nodes = get_geo_node_data(model, techs_no_transmission, node_variable)
    df_links = get_geo_link_data(model, techs_transmission, link_variable)

    src_nodes = ColumnDataSource(df_nodes)
    src_links = ColumnDataSource(df_links)

    bounds = get_geo_bounds(model, as_mercator=True, padding=0.01)

    tooltips_nodes = [("node", "@nodes")] + [
        (i.replace("__", " (") + ")", f"@{i}") for i in df_nodes.columns if "__" in i
    ]

    tooltips_links = [("from", "@node_from"), ("to", "@node_to"), ("data", "@data")]

    # Range bounds must be supplied in web mercator coordinates
    p = figure(
        x_range=bounds.loc["longitude", :].to_list(),
        y_range=bounds.loc["latitude", :].to_list(),
        x_axis_type="mercator",
        y_axis_type="mercator",
        sizing_mode="scale_both",
    )

    p.add_tile(xyz.Stadia.StamenTonerLite, retina=True)
    # p.add_tile(xyz.Stadia.AlidadeSmooth, retina=True)

    p1 = p.scatter(
        x="longitude",
        y="latitude",
        size=15,
        fill_color="red",
        fill_alpha=0.8,
        source=src_nodes,
    )
    p.add_tools(HoverTool(renderers=[p1], tooltips=tooltips_nodes, toggleable=False))

    p2 = p.multi_line(xs="xs", ys="ys", line_width=3, source=src_links)
    p.add_tools(HoverTool(renderers=[p2], tooltips=tooltips_links, toggleable=False))

    return p
