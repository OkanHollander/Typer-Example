"""WeaGLe CLI."""
# ruff: noqa, B008, B006
import os
from shlex import shlex, split
from subprocess import CompletedProcess
from typing import Any, Optional
from pathlib import Path
from enum import Enum

import typer
import yaml
import subprocess

from ansible_collections.vmware.vmware_rest.manual.source.conf import project
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
        filename (str): Docker compose file.
        action (str): Docker compose action. Example 'up'
        services (List[str], optional): List of services defined in the docker compose. Defaults to [].
        verbose (int, optional): Execute verbose command. Defaults to 0.
        command (str, optional): Docker compose command to send on action `exec`. Defaults to "".
        extra_options (str, optional): Extra options to pass over docker compose command. Defaults to "".
        envvars (dict, optional): Environment variables. Defaults to ENVVARS.
        timeout (int, optional): Timeout in seconds. Defaults to None.
        shell (bool, optional): Run the command in a shell. Defaults to False.
        capture_output (bool, optional): Capture stdout and stderr. Defaults to True.
        task_name (str, optional): Name of the task passed. Defaults to "".

    Returns:
        subprocess.CompletedProcess: Result of the command
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
    console.log(f"Stopping project: {project}", style="info")
    run_docker_compose_cmd(
        action="stop",
        filename=Path(f"./projects/{project.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        task_name="Stopping project",
    )