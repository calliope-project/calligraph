import itertools

import panel as pn
from panel.template import BootstrapTemplate

pn.extension("plotly")
pn.extension("perspective")

from calliopevis import pages
from calliopevis.core import ModelContainer


class UIView:

    COORD_ORDERING = ["carriers", "nodes", "techs", "costs"]

    TECHS_COORD_ORDERING = ["supply", "conversion", "storage", "demand", "transmission"]

    def __init__(self, model_container):
        self.model_container = model_container
        self.coord_selectors = {}
        self.view_coord_selectors = self._init_coord_selectors()
        self.pages = self._init_pages()
        self.view_navbar = self._init_navbar()
        self.view_main = pn.Column()
        self.view = self._init_view()

    def _coord_selector(
        self, coord: str, name=None, members=None, as_card=True, multichoice_name=""
    ):
        if name is None:
            name = coord.capitalize()

        if members is None:
            coord_members = (
                self.model_container.model.results.coords[coord].to_index().to_list()
            )
        else:
            coord_members = members

        choice = pn.widgets.MultiChoice(
            value=coord_members, options=coord_members, name=multichoice_name
        )
        self.coord_selectors[coord] = choice

        def filter_all():
            choice.value = coord_members

        btn_filter_all = pn.widgets.Button(icon="plus", name="All")
        btn_filter_all.on_click(lambda event: filter_all())

        def filter_none():
            choice.value = []

        btn_filter_none = pn.widgets.Button(icon="minus", name="None")
        btn_filter_none.on_click(lambda event: filter_none())

        result = [
            choice,
            pn.Row(btn_filter_all, btn_filter_none, styles=dict(margin="-5px 0 5px 0")),
        ]

        if as_card:
            return pn.Card(*result, header="Filter " + name)
        else:
            return pn.Column(*result)

    def _tech_coord_selector(self):
        # if "transmission" in coord:
        #     # return self._coord_selector(coord=coord)
        # else:
        selectors = []
        for base_tech in self.TECHS_COORD_ORDERING:
            members = self.model_container.get_base_tech_members(base_tech)
            selectors.append(
                self._coord_selector(
                    coord="techs_" + base_tech,
                    members=members,
                    as_card=False,
                    multichoice_name=base_tech,
                )
            )
        txt_network_grouping_param = pn.widgets.TextInput(
            name="network_grouping_param", value="inheritance"
        )

        self.coord_selectors["techs"] = pn.widgets.MultiChoice(
            name="techs", options=self._get_tech_coords(), value=self._get_tech_coords()
        )

        pn.bind(
            self._update_tech_coords,
            supply=self.coord_selectors["techs_supply"],
            conversion=self.coord_selectors["techs_conversion"],
            storage=self.coord_selectors["techs_storage"],
            demand=self.coord_selectors["techs_demand"],
            transmission=self.coord_selectors["techs_transmission"],
            watch=True,
        )

        return pn.Card(
            pn.Column(*selectors),
            pn.Row(txt_network_grouping_param),
            header="Filter Techs",
        )

    def _get_tech_coords(self, **kwargs):
        # FIXME: special case for transmission to deal with network grouping
        all_techs = [
            self.coord_selectors["techs_" + base_tech].value
            for base_tech in self.TECHS_COORD_ORDERING
        ]
        return [i for i in itertools.chain.from_iterable(all_techs)]

    def _update_tech_coords(self, **kwargs):
        self.coord_selectors["techs"].value = self._get_tech_coords()

    def _init_coord_selectors(self):
        model_coords = self.model_container.get_model_coords()
        coord_selectors = []

        # Build up the selectors in the order set in COORD_ORDERING,
        # dealing with tech coords in a custom fashion
        for coord in self.COORD_ORDERING:
            if coord == "techs":
                coord_selectors.append(self._tech_coord_selector())
            else:
                coord_selectors.append(self._coord_selector(coord))

        # Add any other coords in the `model_coords` that are not in COORD_ORDERING
        remaining_coords = set(model_coords) - set(self.COORD_ORDERING)
        for coord in remaining_coords:
            coord_selectors.append(self._coord_selector(coord))

        return pn.Column(*coord_selectors)

        # coord_selectors = {
        #     coord: self._coord_selector(coord)
        #     for coord in self.model_container.model.results.coords
        #     if coord != "timesteps"
        # }
        # return pn.Column(*coord_selectors.values())

    def _init_pages(self):
        page_collection = {
            "Home": dict(icon="home", view=pages.page_home),
            "Non-timeseries plots": dict(icon="chart-bar", view=pages.page_pernodetech),
            "Timeseries plots": dict(icon="timeline", view=pages.page_timeseries),
            "Map plots": dict(icon="map-2", view=pages.page_map),
            "Table view": dict(icon="table", view=pages.page_table),
        }
        return page_collection

    def _init_navbar(self):
        buttons = [
            pn.widgets.Button(name=k, icon=v["icon"]) for k, v in self.pages.items()
        ]
        for button in buttons:
            button.on_click(lambda event: self.switch_page(event.obj.name))
        return pn.Row(*buttons)

    def switch_page(self, page):
        self.view_main.clear()
        self.view_main.append(self.pages[page]["view"](self))

    def _init_view(self):
        template = BootstrapTemplate(
            title="CalliopeVis",
            header=[self.view_navbar],
            sidebar=[self.view_coord_selectors],
            main=[self.view_main],
        )
        self.switch_page(list(self.pages.keys())[0])
        return template


def app(path):
    model_container = ModelContainer(path)
    ui_view = UIView(model_container)
    return ui_view.view
