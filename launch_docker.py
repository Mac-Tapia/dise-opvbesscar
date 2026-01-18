#!/usr/bin/env python3
"""
Docker Auto-Launch Script for Iquitos CityLearn Pipeline
Verifica requisitos y lanza el pipeline OE2→OE3 automáticamente
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Tuple, Optional

# Configuración
PROJECT_ROOT = Path(__file__).parent
DOCKER_IMAGE = "iquitos-citylearn:latest"
CONFIG_FILE = "configs/default.yaml"


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(msg: str):
    """Print formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*50}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{msg}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*50}{Colors.ENDC}\n")


def print_success(msg: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")


def print_warning(msg: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")


def print_error(msg: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")


def run_command(cmd: str, capture: bool = False) -> Tuple[int, str]:
    """
    Execute shell command and return exit code and output
    """
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode, result.stdout.strip()
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode, ""
    except Exception as e:
        print_error(f"Command failed: {e}")
        return 1, str(e)


def check_docker() -> bool:
    """Verify Docker is installed and running"""
    print_header("Checking Docker Installation")
    
    returncode, output = run_command("docker --version", capture=True)
    if returncode != 0:
        print_error("Docker is not installed")
        print(f"  Download from: https://www.docker.com/products/docker-desktop")
        return False
    
    print_success(output)
    
    # Check Docker daemon
    returncode, output = run_command("docker ps", capture=True)
    if returncode != 0:
        print_error("Docker daemon is not running")
        if platform.system() == "Windows":
            print("  Start Docker Desktop application")
        elif platform.system() == "Darwin":
            print("  Run: open /Applications/Docker.app")
        else:
            print("  Run: sudo systemctl start docker")
        return False
    
    print_success("Docker daemon is running")
    return True


def check_docker_compose() -> bool:
    """Verify Docker Compose is available"""
    print_header("Checking Docker Compose")
    
    returncode, output = run_command("docker-compose --version", capture=True)
    if returncode != 0:
        print_warning("Docker Compose not found (optional)")
        return False
    
    print_success(output)
    return True


def check_gpu() -> Optional[bool]:
    """Check if NVIDIA GPU is available"""
    print_header("Checking GPU Support")
    
    returncode, output = run_command("nvidia-smi", capture=True)
    if returncode != 0:
        print_warning("NVIDIA GPU not detected - will use CPU")
        return False
    
    print_success("NVIDIA GPU detected:")
    for line in output.split('\n')[:5]:
        print(f"  {line}")
    return True


def check_disk_space() -> bool:
    """Check available disk space"""
    print_header("Checking Disk Space")
    
    try:
        if sys.platform == "win32":
            stat = os.stat(PROJECT_ROOT)
            free_gb = 0  # Windows doesn't have f_bavail in stat
        else:
            stat = os.statvfs(PROJECT_ROOT)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        
        if free_gb > 0 and free_gb < 30:
            print_warning(f"Low disk space: {free_gb:.1f} GB (30 GB recommended)")
            return False
        
        if free_gb > 0:
            print_success(f"Available disk: {free_gb:.1f} GB")
        else:
            print_success("Available disk: OK (cannot determine exact size on this platform)")
        return True
    except Exception as e:
        print_warning(f"Could not check disk space: {e}")
        return True


def check_config() -> bool:
    """Verify config file exists"""
    print_header("Checking Configuration")
    
    config_path = PROJECT_ROOT / CONFIG_FILE
    if not config_path.exists():
        print_error(f"Config file not found: {CONFIG_FILE}")
        return False
    onfig_data
    print_success(f"Config found: {config_path}")
    
    # Validate YAML
    try:
        import yaml
        with open(config_path) as f:
            yaml.safe_load(f)
        print_success(f"Config is valid (OE2 and OE3 sections present)")
        return True
    except Exception as e:
        print_warning(f"Could not validate config: {e}")
        return True


def build_image() -> bool:
    """Build Docker image"""
    print_header("Building Docker Image")
    
    cmd = f'docker build -t {DOCKER_IMAGE} --build-arg BUILDKIT_INLINE_CACHE=1 "{PROJECT_ROOT}"'
    print(f"Command: {cmd}\n")
    
    returncode, _ = run_command(cmd)
    
    if returncode != 0:
        print_error("Build failed")
        return False
    
    print_success("Image built successfully")
    return True


def run_pipeline(use_gpu: bool, skip_oe2: bool = False) -> bool:
    """Run the pipeline inside Docker"""
    print_header("Running OE2→OE3 Pipeline")
    
    # Build volume mounts
    volumes = [
        f'-v "{PROJECT_ROOT}/data:/app/data"',
        f'-v "{PROJECT_ROOT}/outputs:/app/outputs"',
        f'-v "{PROJECT_ROOT}/configs:/app/configs:ro"'
    ]
    
    # GPU support
    gpu_flag = "--gpus all" if use_gpu else ""
    
    # Build command
    docker_cmd = f'docker run -it --rm {gpu_flag} {" ".join(volumes)} {DOCKER_IMAGE}'
    
    if skip_oe2:
        python_cmd = f'python -m scripts.run_oe3_simulate --config {CONFIG_FILE}'
        print_warning("Skipping OE2 (assuming already completed)")
    else:
        python_cmd = f'python -m scripts.run_pipeline --config {CONFIG_FILE}'
        print("Running full OE2→OE3 pipeline")
    
    full_cmd = f'{docker_cmd} {python_cmd}'
    
    print(f"\nContainer command:")
    print(f"  {python_cmd}\n")
    
    print(f"GPU support: {'Enabled' if use_gpu else 'Disabled'}")
    print(f"Volumes: data, outputs, configs")
    print()
    
    returncode, _ = run_command(full_cmd)
    
    if returncode == 0:
        print_success("Pipeline completed successfully!")
        print(f"\nResults available in:")
        print(f"  - outputs/oe3/results/")
        print(f"  - outputs/oe3/checkpoints/")
        print(f"  - outputs/oe3/visualizations/")
        return True
    else:
        print_error("Pipeline execution failed")
        return False


def interactive_menu() -> Tuple[bool, bool]:
    """Show interactive menu for options"""
    print_header("Configuration Options")
    
    # GPU selection
    gpu_available = check_gpu()
    use_gpu = False
    if gpu_available:
        print("\n1. Enable GPU? (Y/n)")
        response = input("  > ").strip().lower()
        use_gpu = response != 'n'
    
    # Skip OE2
    print("\n2. Skip OE2? (y/N)")
    response = input("  > ").strip().lower()
    skip_oe2 = response == 'y'
    
    return use_gpu, skip_oe2


def main():
    """Main execution flow"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Iquitos CityLearn Docker Pipeline Launcher"
    )
    parser.add_argument("--skip-oe2", action="store_true", help="Skip OE2 stages")
    parser.add_argument("--gpu", action="store_true", help="Enable GPU support")
    parser.add_argument("--no-gpu", action="store_true", help="Disable GPU support")
    parser.add_argument("--auto", action="store_true", help="Skip checks and run")
    
    args = parser.parse_args()
    
    print_header("Iquitos CityLearn Docker Pipeline Launcher")
    print(f"Project: {PROJECT_ROOT}")
    print(f"Image: {DOCKER_IMAGE}")
    print(f"Config: {CONFIG_FILE}")
    
    # Run checks
    if not args.auto:
        if not check_docker():
            return 1
        
        check_docker_compose()
        
        use_gpu = args.gpu or (not args.no_gpu and check_gpu())
        skip_oe2 = args.skip_oe2
        
        if not check_disk_space():
            print("\nContinue anyway? (y/N)")
            if input("  > ").strip().lower() != 'y':
                return 1
        
        if not check_config():
            print_error("Please fix configuration before continuing")
            return 1
        
        # Interactive menu if not specified
        if not (args.gpu or args.no_gpu):
            use_gpu, skip_oe2 = interactive_menu()
    else:
        use_gpu = args.gpu and not args.no_gpu
        skip_oe2 = args.skip_oe2
    
    # Build and run
    if not build_image():
        return 1
    
    if not run_pipeline(use_gpu, skip_oe2):
        return 1
    
    print_success("All tasks completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
