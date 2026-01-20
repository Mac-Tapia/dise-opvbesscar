#!/usr/bin/env python3
"""
Docker Build & Deployment Utility for PVBESSCAR
Manage Docker images and containers easily
"""

import subprocess
import sys
import argparse
from pathlib import Path
from typing import Optional
import json


class DockerManager:
    """Manage Docker builds, deployment, and monitoring"""

    def __init__(self, buildkit: bool = True):
        self.buildkit = buildkit
        self.project_root = Path(__file__).parent
        self.env = {"DOCKER_BUILDKIT": "1"} if buildkit else {}

    def run_command(self, cmd: list, check: bool = True) -> int:
        """Execute shell command"""
        print(f"\n📋 Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=check)
        return result.returncode

    def build_image(
        self,
        tag: str = "pvbesscar:latest",
        dockerfile: str = "Dockerfile",
        no_cache: bool = False,
    ) -> int:
        """Build Docker image"""
        cmd = ["docker", "build"]
        
        if no_cache:
            cmd.append("--no-cache")
        
        if self.buildkit:
            cmd.extend(["--build-arg", "BUILDKIT_INLINE_CACHE=1"])
        
        cmd.extend(["-f", dockerfile, "-t", tag, "."])
        
        return self.run_command(cmd)

    def compose_up(
        self,
        compose_file: str = "docker-compose.yml",
        service: Optional[str] = None,
        detach: bool = True,
    ) -> int:
        """Start services with docker-compose"""
        cmd = ["docker-compose", "-f", compose_file, "up"]
        
        if detach:
            cmd.append("-d")
        
        if service:
            cmd.append(service)
        
        return self.run_command(cmd)

    def compose_down(
        self,
        compose_file: str = "docker-compose.yml",
        remove_volumes: bool = False,
    ) -> int:
        """Stop and remove services"""
        cmd = ["docker-compose", "-f", compose_file, "down"]
        
        if remove_volumes:
            cmd.append("-v")
        
        return self.run_command(cmd)

    def compose_logs(
        self,
        compose_file: str = "docker-compose.yml",
        service: Optional[str] = None,
        follow: bool = True,
        tail: int = 100,
    ) -> int:
        """View service logs"""
        cmd = ["docker-compose", "-f", compose_file, "logs"]
        
        if follow:
            cmd.append("-f")
        
        cmd.extend(["--tail", str(tail)])
        
        if service:
            cmd.append(service)
        
        return self.run_command(cmd, check=False)

    def check_health(self, container_name: str) -> bool:
        """Check container health status"""
        cmd = [
            "docker",
            "inspect",
            "--format={{json .State.Health}}",
            container_name,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            health = json.loads(result.stdout)
            
            if health and "Status" in health:
                status = health["Status"]
                print(f"\n✅ {container_name}: {status}")
                return status == "healthy"
            
            return True
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return False

    def stats(self, container_name: Optional[str] = None) -> int:
        """Show container resource usage"""
        cmd = ["docker", "stats"]
        
        if container_name:
            cmd.append(container_name)
        
        return self.run_command(cmd, check=False)

    def prune_cache(self) -> int:
        """Clean up Docker cache"""
        print("\n🧹 Pruning Docker cache...")
        return self.run_command(["docker", "builder", "prune", "--all", "-f"])


def main():
    parser = argparse.ArgumentParser(
        description="Docker management utility for PVBESSCAR"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Build command
    build_parser = subparsers.add_parser("build", help="Build Docker image")
    build_parser.add_argument(
        "--tag",
        default="pvbesscar:latest",
        help="Image tag (default: pvbesscar:latest)",
    )
    build_parser.add_argument(
        "--gpu",
        action="store_true",
        help="Build GPU image (tag: pvbesscar:latest-gpu)",
    )
    build_parser.add_argument(
        "--dev",
        action="store_true",
        help="Build dev image (tag: pvbesscar:dev)",
    )
    build_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore cache during build",
    )
    
    # Up command
    up_parser = subparsers.add_parser("up", help="Start services")
    up_parser.add_argument(
        "--gpu",
        action="store_true",
        help="Use GPU compose file",
    )
    up_parser.add_argument(
        "--dev",
        action="store_true",
        help="Use dev compose file",
    )
    up_parser.add_argument(
        "--service",
        help="Start specific service",
    )
    
    # Down command
    down_parser = subparsers.add_parser("down", help="Stop services")
    down_parser.add_argument(
        "--gpu",
        action="store_true",
        help="Use GPU compose file",
    )
    down_parser.add_argument(
        "--dev",
        action="store_true",
        help="Use dev compose file",
    )
    down_parser.add_argument(
        "-v",
        "--volumes",
        action="store_true",
        help="Remove volumes",
    )
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View service logs")
    logs_parser.add_argument(
        "--gpu",
        action="store_true",
        help="Use GPU compose file",
    )
    logs_parser.add_argument(
        "--dev",
        action="store_true",
        help="Use dev compose file",
    )
    logs_parser.add_argument(
        "--service",
        help="View specific service logs",
    )
    logs_parser.add_argument(
        "--tail",
        type=int,
        default=100,
        help="Number of lines to show (default: 100)",
    )
    
    # Health command
    health_parser = subparsers.add_parser("health", help="Check container health")
    health_parser.add_argument(
        "--gpu",
        action="store_true",
        help="Check GPU containers",
    )
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show resource usage")
    stats_parser.add_argument(
        "--container",
        help="Monitor specific container",
    )
    
    # Clean command
    subparsers.add_parser("clean", help="Clean Docker cache")
    
    args = parser.parse_args()
    
    manager = DockerManager()
    
    if args.command == "build":
        if args.gpu:
            args.tag = "pvbesscar:latest-gpu"
        elif args.dev:
            args.tag = "pvbesscar:dev"
        
        return manager.build_image(
            tag=args.tag,
            no_cache=args.no_cache,
        )
    
    elif args.command == "up":
        compose_file = "docker-compose.yml"
        if args.gpu:
            compose_file = "docker-compose.gpu.yml"
        elif args.dev:
            compose_file = "docker-compose.dev.yml"
        
        return manager.compose_up(
            compose_file=compose_file,
            service=args.service,
        )
    
    elif args.command == "down":
        compose_file = "docker-compose.yml"
        if args.gpu:
            compose_file = "docker-compose.gpu.yml"
        elif args.dev:
            compose_file = "docker-compose.dev.yml"
        
        return manager.compose_down(
            compose_file=compose_file,
            remove_volumes=args.volumes,
        )
    
    elif args.command == "logs":
        compose_file = "docker-compose.yml"
        if args.gpu:
            compose_file = "docker-compose.gpu.yml"
        elif args.dev:
            compose_file = "docker-compose.dev.yml"
        
        return manager.compose_logs(
            compose_file=compose_file,
            service=args.service,
            tail=args.tail,
        )
    
    elif args.command == "health":
        containers = [
            "pvbesscar-pipeline-gpu" if args.gpu else "pvbesscar-pipeline",
        ]
        
        all_healthy = all(
            manager.check_health(container) for container in containers
        )
        
        return 0 if all_healthy else 1
    
    elif args.command == "stats":
        return manager.stats(container_name=args.container)
    
    elif args.command == "clean":
        return manager.prune_cache()
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
