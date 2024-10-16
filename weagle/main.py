import typer
from .commands.docker_commands import docker_app as docker_commands
from .commands.network_commands import network_app as network_commands


app = typer.Typer(rich_help_panel="WeaGLe CLI")

app.add_typer(docker_commands, name="docker", help="Docker Stack Management")
app.add_typer(network_commands, name="network", help="Docker Network Management")

