"""Netobs CLI."""
# ruff: noqa: B008, B006
import os
import shlex
import subprocess  # nosec
import time
from enum import Enum
from pathlib import Path
from subprocess import CompletedProcess  # nosec
from typing import Any, Optional
from urllib.parse import urlparse

import netmiko
import requests
import typer
import yaml
from dotenv import dotenv_values, load_dotenv
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry  # type: ignore
from rich.console import Console
from rich.theme import Theme
from typing_extensions import Annotated

load_dotenv(verbose=True, override=True, dotenv_path=Path("./.env"))
ENVVARS = {**dotenv_values(".env"), **dotenv_values(".setup.env"), **os.environ}

custom_theme = Theme({"info": "cyan", "warning": "bold magenta", "error": "bold red", "good": "bold green"})

console = Console(color_system="truecolor", log_path=False, record=True, theme=custom_theme, force_terminal=True)

app = typer.Typer(help="Run commands for setup and testing", rich_markup_mode="rich", add_completion=False)
containerlab_app = typer.Typer(help="Containerlab related commands.", rich_markup_mode="rich")
app.add_typer(containerlab_app, name="containerlab")

docker_app = typer.Typer(help="Docker and Stacks management related commands.", rich_markup_mode="rich")
app.add_typer(docker_app, name="docker")

lab_app = typer.Typer(help="Overall Lab management related commands.", rich_markup_mode="rich")
app.add_typer(lab_app, name="lab")

setup_app = typer.Typer(help="Lab hosting machine setup related commands.", rich_markup_mode="rich")
app.add_typer(setup_app, name="setup")

utils_app = typer.Typer(help="Utilities and scripts related commands.", rich_markup_mode="rich")
app.add_typer(utils_app, name="utils")


class NetObsScenarios(Enum):
    """NetObs scenarios."""

    BATTERIES_INCLUDED = "batteries-included"
    CH3_COMPLETED = "ch3-completed"
    CH5 = "ch5"
    CH5_COMPLETED = "ch5-completed"
    CH6 = "ch6"
    CH6_COMPLETED = "ch6-completed"
    CH7 = "ch7"
    CH7_COMPLETED = "ch7-completed"
    CH8 = "ch8"
    CH8_COMPLETED = "ch8-completed"
    CH9 = "ch9"
    CH9_COMPLETED = "ch9-completed"
    CH12 = "ch12"
    CH12_COMPLETED = "ch12-completed"
    CH13 = "ch13"
    CH13_COMPLETED = "ch13-completed"


class DockerNetworkAction(Enum):
    """Docker network action."""

    CONNECT = "connect"
    CREATE = "create"
    DISCONNECT = "disconnect"
    INSPECT = "inspect"
    LIST = "ls"
    PRUNE = "prune"
    REMOVE = "rm"


class NautobotClient:
    def __init__(
        self,
        url: str,
        token: str | None = None,
        **kwargs,
    ):
        self.base_url = self._parse_url(url)
        self._token = token
        self.verify_ssl = kwargs.get("verify_ssl", False)
        self.retries = kwargs.get("retries", 3)
        self.timeout = kwargs.get("timeout", 10)
        self.proxies = kwargs.get("proxies", None)
        self._create_session()

    def _parse_url(self, url: str) -> str:
        """Checks if the provided URL has http or https and updates it if needed.

        Args:
            url (str): URL of the grafana instance. ex: "grafana.mylab.com:3000"

        Returns:
            str: a string of the URL. ex: "http://grafana.mylab.com:3000"
        """
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            return f"http://{url}"
        return f"{parsed_url.geturl()}"

    def _create_session(self):
        """
        Creates the requests.Session object and applies the necessary parameters
        """
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        self.session.headers["Accept"] = "application/json"
        self.session.headers["Authorization"] = f"Token {self._token}"
        if self.proxies:
            self.session.proxies.update(self.proxies)

        retry_method = Retry(
            total=self.retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_method)

        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def http_call(
        self,
        method: str,
        url: str,
        data: dict | str | None = None,
        json_data: dict | None = None,
        headers: dict | None = None,
        verify: bool = False,
        params: dict | list[tuple] | None = None,
    ) -> dict:
        """
        Performs the HTTP operation actioned

        **Required Attributes:**

        - `method` (enum): HTTP method to perform: get, post, put, delete, head,
        patch (**required**)
        - `url` (str): URL target (**required**)
        - `data`: Dictionary or byte of request body data to attach to the Request
        - `json_data`: Dictionary or List of dicts to be passed as JSON object/array
        - `headers`: Dictionary of HTTP Headers to attach to the Request
        - `verify`: SSL Verification
        - `params`: Dictionary or bytes to be sent in the query string for the Request
        """
        _request = requests.Request(
            method=method.upper(),
            url=self.base_url + url,
            data=data,
            json=json_data,
            headers=headers,
            params=params,
        )

        # Prepare the request
        _request = self.session.prepare_request(_request)

        # Send the request
        try:
            _response = self.session.send(request=_request, verify=verify, timeout=self.timeout)
            # print(_response.text)
        except Exception as err:
            raise err

        # Raise Error if object already exists
        if "already exists" in _response.text:
            raise ValueError(_response.text)

        # Raise any HTTP errors
        try:
            _response.raise_for_status()
        except Exception as err:
            raise err

        if _response.status_code == 204:
            return {}
        return _response.json()


def strtobool(val: str) -> bool:
    """Convert a string representation of truth to true (1) or false (0).

    Args:
        val (str): String representation of truth.

    Returns:
        bool: True or False
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))


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
        exec_cmd = f"docker compose --project-name {compose_name} -f {docker_compose_file}"

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


def run_cmd(
    exec_cmd: str,
    envvars: dict[str, Any] = ENVVARS,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    shell: bool = False,
    capture_output: bool = False,
    task_name: str = "",
) -> CompletedProcess:
    """Run a command and return the result.

    Args:
        exec_cmd (str): Command to execute
        envvars (dict, optional): Environment variables. Defaults to ENVVARS.
        cwd (str, optional): Working directory. Defaults to None.
        timeout (int, optional): Timeout in seconds. Defaults to None.
        shell (bool, optional): Run the command in a shell. Defaults to False.
        capture_output (bool, optional): Capture stdout and stderr. Defaults to True.
        task_name (str, optional): Name of the task. Defaults to "".

    Returns:
        subprocess.CompletedProcess: Result of the command
    """
    console.log(f"Running command: [orange1 i]{exec_cmd}", style="info")
    result = subprocess.run(
        shlex.split(exec_cmd),
        env=envvars,
        cwd=cwd,
        timeout=timeout,
        shell=shell,  # nosec
        capture_output=capture_output,
        text=True,
        check=False,
    )
    task_name = task_name if task_name else exec_cmd
    if result.returncode == 0:
        console.log(f"Successfully ran: [i]{task_name}", style="good")
    else:
        console.log(f"Issues encountered running: [i]{task_name}", style="warning")
    console.rule(f"End of task: [b i]{task_name}", style="info")
    console.print()
    return result


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
        compose_name="netobs",
    )
    return run_cmd(
        exec_cmd=exec_cmd,
        envvars=envvars,
        timeout=timeout,
        shell=shell,
        capture_output=capture_output,
        task_name=f"{task_name}",
    )

# --------------------------------------#
#                Docker                 #
# --------------------------------------#


@docker_app.command(rich_help_panel="Docker Stack Management", name="build")
def docker_build(
    scenario: Annotated[
        NetObsScenarios, typer.Option("--scenario", "-s", help="Scenario to execute command", envvar="LAB_SCENARIO")
    ],
    services: Annotated[Optional[list[str]], typer.Argument(help="Service(s) to show")] = None,
    verbose: Annotated[bool, typer.Option(help="Verbose mode")] = False,
):
    """Build necessary containers.

    [u]Example:[/u]

    To build all services:
        [i]netobs docker build --scenario batteries-included[/i]

    To build a specific services:
        [i]netobs docker build telegraf-01 telegraf-02 --scenario batteries-included[/i]
    """
    console.log(f"Building service(s): [orange1 i]{services}", style="info")
    run_docker_compose_cmd(
        action="build",
        filename=Path(f"./chapters/{scenario.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        task_name="build stack",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="exec")
def docker_exec(
    service: Annotated[str, typer.Argument(help="Service to execute command")],
    scenario: Annotated[
        NetObsScenarios, typer.Option("--scenario", "-s", help="Scenario to execute command", envvar="LAB_SCENARIO")
    ],
    command: Annotated[str, typer.Argument(help="Command to execute")] = "bash",
    verbose: Annotated[bool, typer.Option(help="Verbose mode")] = False,
):
    """Execute a command in a container.

    [u]Example:[/u]

    To execute a command in a service:
        [i]netobs docker exec telegraf-01 --scenario batteries-included --command bash[/i]

        To execute a command in a service and verbose mode:
        [i]netobs docker exec telegraf-01 --scenario batteries-included --command bash --verbose[/i]
    """
    console.log(f"Executing command in service: [orange1 i]{service}", style="info")
    run_docker_compose_cmd(
        action="exec",
        filename=Path(f"./chapters/{scenario.value}/docker-compose.yml"),
        services=[service],
        command=command,
        verbose=verbose,
        task_name="exec command",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="debug")
def docker_debug(
    scenario: Annotated[
        NetObsScenarios, typer.Option("--scenario", "-s", help="Scenario to execute command", envvar="LAB_SCENARIO")
    ],
    services: Annotated[Optional[list[str]], typer.Argument(help="Service(s) to show")] = None,
    verbose: Annotated[bool, typer.Option(help="Verbose mode")] = False,
):
    """Start docker compose in debug mode.

    [u]Example:[/u]

    To start all services in debug mode:
        [i]netobs docker debug --scenario batteries-included[/i]

    To start a specific service in debug mode:
        [i]netobs docker debug telegraf-01 --scenario batteries-included[/i]
    """
    console.log(f"Starting in debug mode service(s): [orange1 i]{services}", style="info")
    run_docker_compose_cmd(
        action="up",
        filename=Path(f"./chapters/{scenario.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        extra_options="--remove-orphans",
        task_name="debug stack",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="start")
def docker_start(
    scenario: Annotated[
        NetObsScenarios, typer.Option("--scenario", "-s", help="Scenario to execute command", envvar="LAB_SCENARIO")
    ],
    services: Annotated[Optional[list[str]], typer.Argument(help="Service(s) to show")] = None,
    verbose: Annotated[bool, typer.Option(help="Verbose mode")] = False,
):
    """Start all containers.

    [u]Example:[/u]

    To start all services:
        [i]netobs docker start --scenario batteries-included[/i]

    To start a specific service:
        [i]netobs docker start telegraf-01 --scenario batteries-included[/i]
    """
    console.log(f"Starting service(s): [orange1 i]{services}", style="info")
    run_docker_compose_cmd(
        action="up",
        filename=Path(f"./chapters/{scenario.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        extra_options="-d --remove-orphans",
        task_name="start stack",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="stop")
def docker_stop(
    scenario: Annotated[
        NetObsScenarios, typer.Option("--scenario", "-s", help="Scenario to execute command", envvar="LAB_SCENARIO")
    ],
    services: Annotated[Optional[list[str]], typer.Argument(help="Service(s) to show")] = None,
    verbose: Annotated[bool, typer.Option(help="Verbose mode")] = False,
):
    """Stop all containers.

    [u]Example:[/u]

    To stop all services:
        [i]netobs docker stop --scenario batteries-included[/i]

    To stop a specific service:
        [i]netobs docker stop telegraf-01 telegraf-02 --scenario batteries-included[/i]
    """
    console.log(f"Stopping service(s): [orange1 i]{services}", style="info")
    run_docker_compose_cmd(
        action="stop",
        filename=Path(f"./chapters/{scenario.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        task_name="stop stack",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="restart")
def docker_restart(
    scenario: Annotated[
        NetObsScenarios, typer.Option("--scenario", "-s", help="Scenario to execute command", envvar="LAB_SCENARIO")
    ],
    services: Annotated[Optional[list[str]], typer.Argument(help="Service(s) to show")] = None,
    verbose: Annotated[bool, typer.Option(help="Verbose mode")] = False,
):
    """Restart all containers.

    [u]Example:[/u]

    To restart all services:
        [i]netobs docker restart --scenario batteries-included[/i]

    To restart a specific service:
        [i]netobs docker restart telegraf-01 logstash --scenario batteries-included[/i]
    """
    console.log(f"Restarting service(s): [orange1 i]{services}", style="info")
    run_docker_compose_cmd(
        action="restart",
        filename=Path(f"./chapters/{scenario.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        task_name="restart stack",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="logs")
def docker_logs(
    scenario: Annotated[
        NetObsScenarios, typer.Option("--scenario", "-s", help="Scenario to execute command", envvar="LAB_SCENARIO")
    ],
    services: Annotated[Optional[list[str]], typer.Argument(help="Service(s) to show")] = None,
    follow: Annotated[bool, typer.Option("-f", "--follow", help="Follow logs")] = False,
    tail: Optional[int] = typer.Option(None, "-t", "--tail", help="Number of lines to show"),
    verbose: Annotated[bool, typer.Option(help="Verbose mode")] = False,
):
    """Show logs for containers.

    [u]Example:[/u]

    To show logs for all services:
        [i]netobs docker logs --scenario batteries-included[/i]

    To show logs for a specific service:
        [i]netobs docker logs telegraf-01 --scenario batteries-included[/i]

    To show logs for a specific service and follow the logs and tail 10 lines:
        [i]netobs docker logs telegraf-01 --scenario batteries-included --follow --tail 10[/i]
    """
    console.log(f"Showing logs for service(s): [orange1 i]{services}", style="info")
    options = ""
    if follow:
        options += "-f "
    if tail:
        options += f"--tail={tail}"
    run_docker_compose_cmd(
        action="logs",
        filename=Path(f"./chapters/{scenario.value}/docker-compose.yml"),
        services=services if services else [],
        extra_options=options,
        verbose=verbose,
        task_name="show logs",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="ps")
def docker_ps(
    scenario: Annotated[
        NetObsScenarios, typer.Option("--scenario", "-s", help="Scenario to execute command", envvar="LAB_SCENARIO")
    ],
    services: Annotated[Optional[list[str]], typer.Argument(help="Service(s) to show")] = None,
    verbose: Annotated[bool, typer.Option(help="Verbose mode")] = False,
):
    """Show containers.

    [u]Example:[/u]

    To show all services:
        [i]netobs docker ps --scenario batteries-included[/i]

    To show a specific service:
        [i]netobs docker ps telegraf-01 --scenario batteries-included[/i]
    """
    console.log(f"Showing containers for service(s): [orange1 i]{services}", style="info")
    run_docker_compose_cmd(
        action="ps",
        filename=Path(f"./chapters/{scenario.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        task_name="show containers",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="destroy")
def docker_destroy(
    scenario: Annotated[
        NetObsScenarios, typer.Option("--scenario", "-s", help="Scenario to execute command", envvar="LAB_SCENARIO")
    ],
    services: Annotated[Optional[list[str]], typer.Argument(help="Service(s) to show")] = None,
    volumes: Annotated[bool, typer.Option(help="Remove volumes")] = False,
    verbose: Annotated[bool, typer.Option(help="Verbose mode")] = False,
):
    """Destroy containers and resources.

    [u]Example:[/u]

    To destroy all services:
        [i]netobs docker destroy --scenario batteries-included[/i]

    To destroy a specific service:
        [i]netobs docker destroy --scenario batteries-included[/i]

    To destroy a specific service and remove volumes:
        [i]netobs docker destroy telegraf-01 --volumes --scenario batteries-included[/i]

    To destroy all services and remove volumes:
        [i]netobs docker destroy --volumes --scenario batteries-included[/i]
    """
    console.log(f"Destroying service(s): [orange1 i]{services}", style="info")
    run_docker_compose_cmd(
        action="down",
        filename=Path(f"./chapters/{scenario.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        extra_options="--volumes --remove-orphans" if volumes else "--remove-orphans",
        task_name="destroy stack",
    )


@docker_app.command(rich_help_panel="Docker Stack Management", name="rm")
def docker_rm(
    scenario: Annotated[
        NetObsScenarios, typer.Option("--scenario", "-s", help="Scenario to execute command", envvar="LAB_SCENARIO")
    ],
    services: Annotated[Optional[list[str]], typer.Argument(help="Service(s) to show")] = None,
    volumes: Annotated[bool, typer.Option(help="Remove volumes")] = False,
    force: Annotated[bool, typer.Option(help="Force removal of containers")] = False,
    verbose: Annotated[bool, typer.Option(help="Verbose mode")] = False,
):
    """Remove containers.

    [u]Example:[/u]

    To remove all services:
        [i]netobs docker rm --scenario batteries-included[/i]

    To remove a specific service:
        [i]netobs docker rm telegraf-01 --scenario batteries-included[/i]

    To remove a specific service and remove volumes:
        [i]netobs docker rm telegraf-01 --volumes --scenario batteries-included[/i]

    To remove all services and remove volumes:
        [i]netobs docker rm --volumes --scenario batteries-included[/i]

    To remove all services and force removal of containers:
        [i]netobs docker rm --force --scenario batteries-included[/i]

    To force removal of a specific service and remove volumes:
        [i]netobs docker rm telegraf-01 --volumes --force --scenario batteries-included[/i]
    """
    extra_options = "--stop "
    if force:
        extra_options += "--force "
    if volumes:
        extra_options += "--volumes "
    console.log(f"Removing service(s): [orange1 i]{services}", style="info")
    run_docker_compose_cmd(
        action="rm",
        filename=Path(f"./chapters/{scenario.value}/docker-compose.yml"),
        services=services if services else [],
        verbose=verbose,
        extra_options=extra_options,
        task_name="remove containers",
    )


@docker_app.command("network")
def docker_network(
    action: Annotated[DockerNetworkAction, typer.Argument(..., help="Action to perform", case_sensitive=False)],
    name: Annotated[str, typer.Option("-n", "--name", help="Network name")] = "network-observability",
    driver: Annotated[str, typer.Option(help="Network driver")] = "bridge",
    subnet: Annotated[str, typer.Option(help="Network subnet")] = "198.51.100.0/24",
    verbose: Annotated[bool, typer.Option(help="Verbose mode")] = False,
):
    """Manage docker network."""
    console.log(f"Network {action.value}: [orange1 i]{name}", style="info")
    exec_cmd = f"docker network {action.value}"
    if driver and action.value == "create":
        exec_cmd += f" --driver={driver} "
    if subnet and action.value == "create":
        exec_cmd += f" --subnet={subnet}"
    if action.value != "ls" and action.value != "prune":
        exec_cmd += f" {name}"
    run_cmd(
        exec_cmd=exec_cmd,
        task_name=f"network {action.value}",
    )

