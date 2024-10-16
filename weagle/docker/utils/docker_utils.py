from subprocess import run
from pathlib import Path
from typing import List


def run_docker_compose_cmd(action: str, filename: Path, services: List[str], verbose: bool, task_name: str,
                           extra_options: str = ""):
    service_list = " ".join(services) if services else ""
    cmd = f"docker-compose -f {filename} {action} {service_list} {extra_options}"
    if verbose:
        print(f"Running command: {cmd}")
    run(cmd, shell=True, check=True)


def run_cmd(exec_cmd: str, task_name: str, verbose: bool):
    if verbose:
        print(f"{task_name}: {exec_cmd}")
    run(exec_cmd, shell=True, check=True)
