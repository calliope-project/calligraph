import click
import panel as pn

import calligraph


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--port",
    "-p",
    help="Port on which to serve the app. By default (0), a random available port is chosen.",
    default=0,
)
@click.option("--no-browser", "-nb", help="Do not open a browser.", is_flag=True)
@click.option(
    "--development",
    help="Run in development mode. Currently this enables autoreload on code change.",
    is_flag=True,
)
@click.version_option()
def calligraph_cli(path, no_browser, port, development):
    """
    Opens the Calliope NetCDF model file given by PATH in an interactive visualisation
    tool.

    """
    app = calligraph.ui.app(path)
    devt_kwargs = dict(autoreload=True) if development is True else dict()
    pn.serve(port=port, panels=app, show=False if no_browser else True, **devt_kwargs)


if __name__ == "__main__":
    calligraph_cli()
