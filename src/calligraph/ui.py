import itertools

import panel as pn
from panel.template import BootstrapTemplate

from calligraph import pages
from calligraph.core import ModelContainer

pn.extension("plotly")
pn.extension("perspective")
pn.extension("gridstack")
pn.extension(design="bootstrap")


class UIView:

    COORD_ORDERING = ["carriers", "nodes", "techs", "costs"]
    TECHS_COORD_ORDERING = ["supply", "conversion", "storage", "demand", "transmission"]
    HEADER_BACKGROUND_COLOR = "#55b3f9"
    HEADER_TEXT_COLOR = "#ffffff"

    def __init__(self, model_container):
        self.model_container = model_container
        self.coord_selectors = {}
        self.filter_coords = []
        self.view_coord_selectors = self._init_coord_selectors()
        self.pages = self._init_pages()
        self.view_main = self._init_view_main()
        self.view_navbar = self._init_navbar()
        self.view = self._init_view()
        self.switch_page(list(self.pages.keys())[0])
        self._resettable_widgets = {}
        self._resettable_widgets_defaults = {}

    def __get_transmission_groups(self, group_param=""):
        # FIXME this function can easily return nonsense depending on
        # what `group_param` is passed in
        transmission_techs = self.coord_selectors["techs_transmission"].options
        model = self.model_container.model

        if group_param in model.inputs:
            groups = (
                model.inputs[group_param]
                .sel(techs=transmission_techs)
                .to_dataframe()
                .groupby(group_param)
                .groups
            )
        else:  # e.g. it is None or ""
            groups = {i: [i] for i in transmission_techs}

        return groups

    def _coord_selector(
        self, coord: str, name=None, members=None, as_card=True, multichoice_name=""
    ):
        if name is None:
            name = coord.capitalize()

        if members is None:
            coord_members = (
                self.model_container.combined_data.coords[coord].to_index().to_list()
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
            return pn.Card(*result, title="Filter " + name)
        else:
            return pn.Column(*result)

    def __get_tech_coord_selector(self, base_tech):
        members = self.model_container.get_base_tech_members(base_tech)
        selector = self._coord_selector(
            coord="techs_" + base_tech,
            members=members,
            as_card=False,
            multichoice_name=base_tech,
        )
        return selector

    def _init_transmission_groups(self, group_param):
        self.transmission_groups = self.__get_transmission_groups(group_param)

    def _update_transmission_groups(self, group_param):
        # FIXME: this should return some feedback based on whether or not the
        # chosen grouping exists as a variable
        self._init_transmission_groups(group_param)
        new_options = list(self.transmission_groups.keys())
        self.coord_selectors["techs_transmission_grouped"].options = new_options
        self.coord_selectors["techs_transmission_grouped"].value = new_options

    def __get_transmission_coord_selector(self, group_param):
        transmission_techs = self.model_container.get_base_tech_members("transmission")
        self.coord_selectors["techs_transmission"] = pn.widgets.MultiChoice(
            name="transmission", options=transmission_techs, value=transmission_techs
        )
        self._init_transmission_groups(group_param)
        members = list(self.transmission_groups.keys())
        selector = self._coord_selector(
            coord="techs_transmission_grouped",
            members=members,
            as_card=False,
            multichoice_name="transmission",
        )
        return selector

    def _tech_coord_selector(self):
        transmission_group_param = ""

        selectors = []
        for base_tech in self.TECHS_COORD_ORDERING:
            if base_tech == "transmission":
                selectors.append(
                    self.__get_transmission_coord_selector(transmission_group_param)
                )
            else:
                selectors.append(self.__get_tech_coord_selector(base_tech))

        txt_network_grouping_param = pn.widgets.TextInput(
            name="network_grouping_param", value=transmission_group_param
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

        pn.bind(
            self._update_tech_transmission_coords,
            transmission_grouped=self.coord_selectors["techs_transmission_grouped"],
            watch=True,
        )

        pn.bind(
            self._update_transmission_groups,
            group_param=txt_network_grouping_param,
            watch=True,
        )

        return pn.Card(
            pn.Column(*selectors, styles=dict(margin="0")),
            pn.Row(txt_network_grouping_param, styles=dict(margin="0 0 8px 0")),
            title="Filter Techs",
            width=320,
        )

    def _update_tech_coords(self, **kwargs):
        self.coord_selectors["techs"].value = self._get_tech_coords()

    def _update_tech_transmission_coords(self, transmission_grouped):
        ungrouped_transmission = [
            i
            for i in itertools.chain.from_iterable(
                self.transmission_groups[j] for j in transmission_grouped
            )
        ]
        self.coord_selectors["techs_transmission"].value = ungrouped_transmission

    def _get_tech_coords(self, **kwargs):
        # FIXME: special case for transmission to deal with network grouping
        all_techs = [
            self.coord_selectors["techs_" + base_tech].value
            for base_tech in self.TECHS_COORD_ORDERING
        ]
        return [i for i in itertools.chain.from_iterable(all_techs)]

    def _init_coord_selectors(self):
        model_coords = self.model_container.get_model_coords()
        coord_selectors = []

        # Build up the selectors in the order set in COORD_ORDERING,
        # dealing with tech coords in a custom fashion
        for coord in self.COORD_ORDERING:
            self.filter_coords.append(coord)
            if coord == "techs":
                coord_selectors.append(self._tech_coord_selector())
            else:
                coord_selectors.append(self._coord_selector(coord))

        # Add any other coords in the `model_coords` that are not in COORD_ORDERING
        remaining_coords = set(model_coords) - set(self.COORD_ORDERING)
        for coord in remaining_coords:
            self.filter_coords.append(coord)
            coord_selectors.append(self._coord_selector(coord))

        # Toggle for including inputs
        self.switch_inputs = switch_inputs = pn.widgets.Switch(
            value=True, name="Include inputs"
        )
        row_switch_inputs = pn.Row("Include input variables", switch_inputs)

        pn.bind(
            self.model_container.update_variables,
            include_inputs=switch_inputs,
            watch=True,
        )

        return pn.Column(row_switch_inputs, *coord_selectors)

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
        # Assumes that every page generator function in self.pages[page]["view"] either
        # returns a single appropriate Panel object such as pn.Column or a list of a
        # maximum of panel of two panel objects
        content = self.pages[page]["view"](self)
        for i in range(len(self.view.main)):
            self.view.main[i].clear()
        if isinstance(content, list):
            gstack = pn.layout.gridstack.GridStack(
                sizing_mode="stretch_both",
                min_height=600,
                allow_drag=False,
                allow_resize=False,
            )
            gstack[:, 0:6] = content[0]
            gstack[:, 6:12] = content[1]
            self.view.main[0].append(gstack)
        else:
            self.view.main[0].append(content)

    def _init_view_main(self):
        return pn.Column()

    def _init_view(self):
        view = BootstrapTemplate(
            header_background=self.HEADER_BACKGROUND_COLOR,
            header_color=self.HEADER_TEXT_COLOR,
            title=self.model_container.name,
            header=[self.view_navbar],
            sidebar=[self.view_coord_selectors],
            main=[],
        )
        view.main.append(pn.Column())  # Column 0
        # view.main.append(pn.Column())  # Column 1
        return view

    def initialise_resettable_widget(
        self, id, name="Variable", variables="variables", value="flow_cap"
    ):
        widget = pn.widgets.Select(
            name=name, value=value, options=self.model_container.variables[variables]
        )
        self._resettable_widgets[id] = widget
        self._resettable_widgets_defaults[id] = variables

        pn.bind(
            self.reset_widget,
            id=id,
            switch_inputs=self.switch_inputs,  # Dummy argument
            watch=True,
        )

        return widget

    def reset_widget(self, id, *args, **kwargs):
        variables = self._resettable_widgets_defaults[id]
        self._resettable_widgets[id].options = self.model_container.variables[variables]


def app(path):
    model_container = ModelContainer(path)
    ui_view = UIView(model_container)
    return ui_view.view
