import click
import panel as pn

import calliopevis


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--browser/--no-browser", help="Whether to open a browser or not.", default=True
)
@click.option("--port", help="Port on which to serve the app.", default=18080)
def calliopevis_cli(path, browser, port):
    app = calliopevis.ui.app(path)
    pn.serve(
        port=port, panels=app, show=browser, autoreload=True
    )  # FIXME remove autoreload for distribution


if __name__ == "__main__":
    calliopevis_cli()
