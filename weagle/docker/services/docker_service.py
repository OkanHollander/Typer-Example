from weagle.docker.utils.docker_utils import run_docker_compose_cmd, run_cmd
from pathlib import Path
from weagle.docker.models.project_folders import ProjectFolders
from typing import Optional, List


class DockerService:
    @staticmethod
    def start(project: ProjectFolders,
              services: Optional[List[str]],
              verbose: bool,):
        # Logic to start Docker services
        run_docker_compose_cmd("up", Path(f"./projects/{project.value}/docker-compose.yml"), services, verbose,
                               "Starting project", extra_options="-d")

    @staticmethod
    def stop(project: ProjectFolders, services: Optional[List[str]], verbose: bool):
        # Logic to stop Docker services
        run_docker_compose_cmd("down", Path(f"./projects/{project.value}/docker-compose.yml"), services, verbose,
                               "Stopping project")

    @staticmethod
    def debug(project: ProjectFolders, services: Optional[List[str]], verbose: bool):
        # Logic to debug Docker service
        run_docker_compose_cmd("up", Path(f"./projects/{project.value}/docker-compose.yml"), services, verbose,
                               "Debugging service")

    @staticmethod
    def restart(project: ProjectFolders, services: Optional[List[str]], verbose: bool):
        # Logic to restart Docker services
        run_docker_compose_cmd("restart", Path(f"./projects/{project.value}/docker-compose.yml"), services, verbose,
                               "Restarting project")

    @staticmethod
    def destroy(project: ProjectFolders, services: Optional[List[str]], verbose: bool):
        # Logic to destroy Docker services
        run_docker_compose_cmd("down --volumes", Path(f"./projects/{project.value}/docker-compose.yml"), services,
                               verbose,
                               "Destroying project")

    @staticmethod
    def docker_ps(project: ProjectFolders, services: Optional[List[str]], verbose: bool):
        # Logic to list Docker services
        run_docker_compose_cmd("ps", Path(f"./projects/{project.value}/docker-compose.yml"), services, verbose,
                               "Listing services")

    @staticmethod
    def manage_network(action: str, name: str, driver: str, subnet: str, verbose: bool):
        # Logic to manage Docker networks
        exec_cmd = f"docker network {action}"
        if action == "create":
            exec_cmd += f" --driver {driver} --subnet {subnet} {name}"
        run_cmd(exec_cmd, f"Network {action}", verbose)
