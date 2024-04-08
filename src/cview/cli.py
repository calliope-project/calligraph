import click
import panel as pn

import cview


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--port", "-p", help="Port on which to serve the app.", default=18080)
@click.option("--no-browser", "-nb", help="Do not open a browser.", is_flag=True)
@click.option(
    "--development",
    help="Run in development mode. Currently this enables autoreload on code change.",
    is_flag=True,
)
def cview_cli(path, no_browser, port, development):
    """
    Opens the Calliope NetCDF model file given by PATH in an interactive visualisation
    tool.

    """
    app = cview.ui.app(path)
    devt_kwargs = dict(autoreload=True) if development is True else dict()
    pn.serve(port=port, panels=app, show=False if no_browser else True, **devt_kwargs)


if __name__ == "__main__":
    cview_cli()
