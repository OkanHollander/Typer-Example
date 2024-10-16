"""WeaGLe CLI."""
# ruff: noqa, B008, B006
import os
from shlex import split
from subprocess import CompletedProcess
from typing import Any, Optional
from pathlib import Path
from enum import Enum

import typer
import yaml
import subprocess

from rich.console import Console
from rich.theme import Theme
from typing_extensions import Annotated
from dotenv import load_dotenv, dotenv_values

load_dotenv(verbose=True, override=True, dotenv_path=Path("./.env"))
ENVVARS = {**dotenv_values(".env"), **dotenv_values(".setup.env"), **os.environ}

############
# Typer App
############
custom_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "good": "bold green",
    }
)
console = Console(
    color_system="truecolor",
    log_path=False,
    record=True,
    theme=custom_theme,
    force_terminal=True,
)

app = typer.Typer(
    help="WeaGLe CLI",
    add_completion=True,
)

docker_app = typer.Typer(help="Docker related commands", add_completion=True)
app.add_typer(docker_app, name="docker")


############
# Classes
############
class ProjectFolders(Enum):
    """Project folders."""
    PROJECT_01 = "project_01"
    PROJECT_02 = "project_02"
    PROJECT_03 = "project_03"
    PROJECT_04 = "project_04"
    PROJECT_05 = "project_05"


class DockerNetworkAction(Enum):
    """Docker network action."""

    CONNECT = "connect"
    CREATE = "create"
    DISCONNECT = "disconnect"
    INSPECT = "inspect"
    LIST = "ls"
    PRUNE = "prune"
    REMOVE = "rm"


############
# Functions
############
def strtobool(val: str) -> bool:
    """
    Convert a string representation of truth to a boolean.

    Args:
        val (str): A string representing a boolean value. Accepted values are
                   "true", "t", "yes", "y", "1" for True and
                   "false", "f", "no", "n", "0" for False.

    Returns:
        bool: The boolean value corresponding to the string.

    Raises:
        ValueError: If the string does not represent a valid boolean value.
    """
    val = val.lower()
    if val in {"true", "t", "yes", "y", "1"}:
        return True
    elif val in {"false", "f", "no", "n", "0"}:
        return False
    else:
        raise ValueError(f"{val} is not a valid boolean value")


def is_truthy(arg: Any) -> bool:
    """Convert "truthy" strings into Booleans.

    Examples:
    ```python
        >>> is_truthy('yes')
        True
    ```

    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.
    """
    if isinstance(arg, bool):
        return arg
    if arg is None:
        return False
    return bool(strtobool(arg))


def run_cmd(
        exec_cmd: str,
        envvars: dict[str, Any] = ENVVARS,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        shell: bool = False,
        capture_output: bool = False,
        task_name: str = "",
) -> CompletedProcess:
    console.log(f"Running command: {exec_cmd}", style="info")
    result = subprocess.run(
        split(exec_cmd),
        env=envvars,
        cwd=cwd,
        timeout=timeout,
        shell=shell,
        capture_output=capture_output,
        text=True,
        check=False,
    )
    """
        Execute a shell command and log the output.

        Args:
            exec_cmd (str): The command to execute.
            envvars (dict[str, Any], optional): Environment variables to set for the command. Defaults to ENVVARS.
            cwd (Optional[str], optional): The working directory to run the command in. Defaults to None.
            timeout (Optional[int], optional): The timeout for the command in seconds. Defaults to None.
            shell (bool, optional): Whether to use the shell as the program to execute. Defaults to False.
            capture_output (bool, optional): Whether to capture the output of the command. Defaults to False.
            task_name (str, optional): A name for the task to be used in logging. Defaults to "".

        Returns:
            CompletedProcess: The result of the executed command.
        """
    task_name = task_name if task_name else exec_cmd
    if result.returncode == 0:
        console.log(f"{task_name} completed successfully", style="good")
    else:
        console.log(f"{task_name} failed", style="error")
    console.rule(f"End of task: [b i]{task_name}", style="info")
    console.print()
    return result


def docker_compose_cmd(
        compose_action: str,
        docker_compose_file: Path,
        services: list[str] = [],
        verbose: int = 0,
        extra_options: str = "",
        command: str = "",
        compose_name: str = "",
) -> str:
    """Create docker-compose command to execute.

    Args:
        compose_action (str): Docker Compose action to run.
        docker_compose_file (Path): Docker compose file.
        services (List[str], optional): List of specifics container to action. Defaults to [].
        verbose (int, optional): Verbosity. Defaults to 0.
        extra_options (str, optional): Extra docker compose flags to pass to the command line. Defaults to "".
        command (str, optional): Command to execute in docker compose. Defaults to "".
        compose_name (str, optional): Name to give to the docker compose project. Defaults to PROJECT_NAME.

    Returns:
        str: Docker compose command
    """
    if is_truthy(ENVVARS.get("DOCKER_COMPOSE_WITH_HASH", None)):
        exec_cmd = f"docker-compose --project-name {compose_name} -f {docker_compose_file}"
    else:
        exec_cmd = f"docker-compose --project-name {compose_name} -f {docker_compose_file}"

    if verbose:
        exec_cmd += " --verbose"
    exec_cmd += f" {compose_action}"

    if extra_options:
        exec_cmd += f" {extra_options}"
    if services:
        exec_cmd += f" {' '.join(services)}"
    if command:
        exec_cmd += f" {command}"

    return exec_cmd


def run_docker_compose_cmd(
        filename: Path,
        action: str,
        services: list[str] = [],
        verbose: int = 0,
        command: str = "",
        extra_options: str = "",
        envvars: dict[str, Any] = ENVVARS,
        timeout: Optional[int] = None,
        shell: bool = False,
        capture_output: bool = False,
        task_name: str = "",
) -> subprocess.CompletedProcess:
    """Run a docker compose command.

    Args:
        filename (Path): Path to the Docker compose file.
        action (str): Docker compose action to execute (e.g., 'up', 'down', 'build').
        services (list[str], optional): List of services to target. Defaults to an empty list.
        verbose (int, optional): Verbosity level. Defaults to 0.
        command (str, optional): Additional command to execute with docker compose. Defaults to an empty string.
        extra_options (str, optional): Extra options to pass to the docker compose command. Defaults to an empty string.
        envvars (dict[str, Any], optional): Environment variables to set for the command. Defaults to ENVVARS.
        timeout (Optional[int], optional): Timeout for the command in seconds. Defaults to None.
        shell (bool, optional): Whether to use the shell as the program to execute. Defaults to False.
        capture_output (bool, optional): Whether to capture the output of the command. Defaults to False.
        task_name (str, optional): Name of the task for logging purposes. Defaults to an empty string.

    Returns:
        subprocess.CompletedProcess: The result of the executed command.

    Raises:
        typer.Exit: If the specified Docker compose file does not exist.
    """
    if not filename.exists():
        console.log(f"File not found: [orange1 i]{filename}", style="error")
        raise typer.Exit(1)

    exec_cmd = docker_compose_cmd(
        action,
        docker_compose_file=filename,
        services=services,
        command=command,
        verbose=verbose,
        extra_options=extra_options,
        compose_name="weagle",
    )
    return run_cmd(
        exec_cmd=exec_cmd,
        envvars=envvars,
        timeout=timeout,
        shell=shell,
        capture_output=capture_output,
        task_name=f"{task_name}",
    )


############
# Docker
############
@docker_app.command(rich_help_panel="Docker Stack Management", name="build")
def docker_build(
        project: Annotated[
            ProjectFolders,
            typer.Option("--project", "-p", help="Project folder", envvar="PROJECT")
        ],
        services: Annotated[Optional[list[str]], typer.Argument(help="Services to build")] = None,
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
):
    """
    Build the specified Docker project and its services.

    Args:
        project (ProjectFolders): The project folder to build.
        services (Optional[list[str]], optional): List of services to build. Defaults to None.
        verbose (bool, optional): Enable verbose mode. Defaults to False.
    [u]Examples:[/u]

    To Build all services:
        [i]weagle docker build --project project_01[/i]

    To Build specific services:
        [i]weagle docker build service_01 service_02 --project project_01 [/i]
    """
    console.log(f"Building project: {project}", style="info")
    run_docker_compose_cmd(
        action="build",
        filename=Path(f"./projects/{project.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        task_name="Building project",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="start")
def docker_start(
        project: Annotated[
            ProjectFolders,
            typer.Option("--project", "-p", help="Project folder", envvar="PROJECT")
        ],
        services: Annotated[Optional[list[str]], typer.Argument(help="Services to start")] = None,
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
        detached: Annotated[bool, typer.Option("--detached", "-d", help="Detached Mode")] = False,
):
    """
        Start the specified Docker project and its services.

    Args:
        project (ProjectFolders): The project folder to start.
        services (Optional[list[str]], optional): List of services to start. Defaults to None.
        verbose (bool, optional): Enable verbose mode. Defaults to False.
        detached (bool, optional): Run containers in detached mode. Defaults to False.

    [u]Examples:[/u]

    To start all services:
        [i]weagle docker start --project project_01[/i]

    To start specific services:
        [i]weagle docker start service_01 --project project_01[/i]
    """
    console.log(f"Starting project: {project}", style="info")
    run_docker_compose_cmd(
        action="up",
        filename=Path(f"./projects/{project.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        task_name="Starting project",
        extra_options="-d" if detached else "",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="stop")
def docker_stop(
        project: Annotated[
            ProjectFolders,
            typer.Option("--project", "-p", help="Project folder", envvar="PROJECT")
        ],
        services: Annotated[Optional[list[str]], typer.Argument(help="Services to stop")] = None,
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
):
    """
        Stop the specified Docker project and its services.

        Args:
            project (ProjectFolders): The project folder to stop.
            services (Optional[list[str]], optional): List of services to stop. Defaults to None.
            verbose (bool, optional): Enable verbose mode. Defaults to False.

        [u]Examples:[/u]

        To stop all services:
            [i]weagle docker stop --project project_01[/i]

        To stop specific services:
            [i]weagle docker stop service_01 --project project_01[/i]

        """
    console.log(f"Stopping project: {project}", style="info")
    run_docker_compose_cmd(
        action="stop",
        filename=Path(f"./projects/{project.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        task_name="Stopping project",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="exec")
def docker_exec(
        project: Annotated[
            ProjectFolders,
            typer.Option("--project", "-p", help="Project folder", envvar="PROJECT")
        ],
        services: Annotated[str, typer.Argument(help="Service to execute command")],
        command: Annotated[str, typer.Argument(help="Command to execute")] = "bash",
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
):
    """
    Execute a command in a running container.

    Args:
        project (ProjectFolders): The project folder to execute the command in.
        services (str): The service to execute the command in.
        command (str): The command to execute.
        verbose (bool, optional): Enable verbose mode. Defaults to False.

    [u]Examples:[/u]

    To execute a command in a service:
        [i]weagle docker exec --project project_01 service_01 --command "ls -la"[/i]
    """
    console.log(f"Executing command: {command}", style="info")
    run_docker_compose_cmd(
        action="exec",
        filename=Path(f"./projects/{project.value}/docker-compose.yml"),
        services=[services],
        command=command,
        verbose=verbose,
        task_name="Executing command",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="debug")
def docker_debug(
        project: Annotated[
            ProjectFolders,
            typer.Option("--project", "-p", help="Project folder", envvar="PROJECT")
        ],
        services: Annotated[Optional[list[str]], typer.Argument(help="Service to debug")],
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
):
    """
    Debug a service.

    Args:
        project (ProjectFolders): The project folder to debug.
        services (str): The service to debug.
        verbose (bool, optional): Enable verbose mode. Defaults to False.

    [u]Examples:[/u]

    To debug a service:
        [i]weagle docker debug service_01 --project project_01[/i]
    """
    console.log(f"Debugging service: {services}", style="info")
    run_docker_compose_cmd(
        action="up",
        filename=Path(f"./projects/{project.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        task_name="Debugging service",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="restart")
def docker_restart(
        project: Annotated[
            ProjectFolders,
            typer.Option("--project", "-p", help="Project folder", envvar="PROJECT")
        ],
        services: Annotated[Optional[list[str]], typer.Argument(help="Services to restart")] = None,
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
):
    """
    Restart the specified Docker project and its services.

    Args:
        project (ProjectFolders): The project folder to restart.
        services (Optional[list[str]], optional): List of services to restart. Defaults to None.
        verbose (bool, optional): Enable verbose mode. Defaults to False.

    [u]Examples:[/u]

    To restart all services:
        [i]weagle docker restart --project project_01[/i]

    To restart specific services:
        [i]weagle docker restart service_01 --project project_01[/i]
    """
    console.log(f"Restarting project: {project}", style="info")
    run_docker_compose_cmd(
        action="restart",
        filename=Path(f"./projects/{project.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        task_name="Restarting project",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="logs")
def docker_logs(
        project: Annotated[
            ProjectFolders,
            typer.Option("--project", "-p", help="Project folder", envvar="PROJECT")
        ],
        services: Annotated[Optional[list[str]], typer.Argument(help="Services to get logs")] = None,
        follow: Annotated[bool, typer.Option("--follow", "-f", help="Follow logs")] = False,
        tail: Annotated[
            int, typer.Option("--tail", "-t", help="Number of lines to show from the end of the logs")] = 100,
        verbose: Annotated[bool, typer.Option(help="Verbose Mode")] = False,
):
    """
    Get the logs of the specified Docker project and its services.

    Args:
        project (ProjectFolders): The project folder to get logs from.
        services (Optional[list[str]], optional): List of services to get logs from. Defaults to None.
        follow (bool, optional): Follow logs. Defaults to False.
        tail (int, optional): Number of lines to show from the end of the logs. Defaults to 100.
        verbose (bool, optional): Enable verbose mode. Defaults to False.

    [u]Examples:[/u]

    To get logs from all services:
        [i]weagle docker logs --project project_01[/i]

    To get logs from specific services:
        [i]weagle docker logs service_01 --project project_01[/i]

    """
    console.log(f"Getting logs for project: {project}", style="info")
    options = ""
    if follow:
        options += " -f"
    if tail:
        options += f" --tail={tail}"
    run_docker_compose_cmd(
        action="logs",
        filename=Path(f"./projects/{project.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        task_name="Getting logs",
        extra_options=options,
    )
