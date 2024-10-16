import typer
from weagle.docker.services.docker_service import DockerService
from typing import Annotated

network_app = typer.Typer(rich_help_panel="Docker Network Management")

@network_app.command(name="network")
def docker_network(
        action: Annotated[str, typer.Argument(..., help="Network action")],
        name: Annotated[str, typer.Option("--name", "-n", help="Network name")] = "weagle-network",
        driver: Annotated[str, typer.Option(help="Network driver")] = "bridge",
        subnet: Annotated[str, typer.Option(help="Network subnet")] = "192.168.1.0/24",
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
):
    DockerService.manage_network(action, name, driver, subnet, verbose)
