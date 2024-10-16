import typer
from weagle.docker.models.project_folders import ProjectFolders
from weagle.docker.services.docker_service import DockerService
from typing import Optional, Annotated

docker_app = typer.Typer(rich_help_panel="Docker Stack Management")

@docker_app.command(name="debug")
def docker_debug(
        project: Annotated[ProjectFolders, typer.Option("--project", "-p", help="Project folder")],
        services: Annotated[Optional[list[str]], typer.Argument(help="Service to debug")] = None,
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
):
    DockerService.debug(project, services, verbose)

@docker_app.command(name="restart")
def docker_restart(
        project: Annotated[ProjectFolders, typer.Option("--project", "-p", help="Project folder")],
        services: Annotated[Optional[list[str]], typer.Argument(help="Services to restart")] = None,
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
):
    DockerService.restart(project, services, verbose)
#
@docker_app.command(name="start")
def docker_start(
        project: Annotated[ProjectFolders, typer.Option("--project", "-p", help="Project folder")],
        services: Annotated[Optional[list[str]], typer.Argument(help="Services to start")] = None,
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
):
    DockerService.start(project, services, verbose)

@docker_app.command(name="stop")
def docker_stop(
        project: Annotated[ProjectFolders, typer.Option("--project", "-p", help="Project folder")],
        services: Annotated[Optional[list[str]], typer.Argument(help="Services to stop")] = None,
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
):
    DockerService.stop(project, services, verbose)

@docker_app.command(name="destroy")
def docker_destroy(
        project: Annotated[ProjectFolders, typer.Option("--project", "-p", help="Project folder")],
        services: Annotated[Optional[list[str]], typer.Argument(help="Services to destroy")] = None,
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
):
    DockerService.destroy(project, services, verbose)

@docker_app.command(name="ps")
def docker_ps(
        project: Annotated[ProjectFolders, typer.Option("--project", "-p", help="Project folder")],
        services: Annotated[Optional[list[str]], typer.Argument(help="Services to list")] = None,
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
):
    DockerService.docker_ps(project, services, verbose)