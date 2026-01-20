#!/usr/bin/env python3
"""
PVBESSCAR Kubernetes Deployment Manager
Gestionar deployment en Kubernetes con MongoDB
"""

import subprocess
import json
import sys
from pathlib import Path
from typing import Dict, List

class K8sManager:
    """Manage Kubernetes deployment"""
    
    def __init__(self):
        self.namespace = "pvbesscar"
        self.project_root = Path(__file__).parent
        
    def run_command(self, cmd: List[str], check: bool = True) -> Dict:
        """Execute kubectl command"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': str(e)
            }
    
    def check_k8s(self) -> bool:
        """Check if kubectl is available"""
        result = self.run_command(['kubectl', 'version', '--client'], check=False)
        return result['success']
    
    def deploy(self) -> bool:
        """Deploy to Kubernetes"""
        if not self.check_k8s():
            print("❌ kubectl not available")
            return False
        
        print("🚀 Deploying PVBESSCAR to Kubernetes...")
        
        # Create namespace
        print("\n📁 Creating namespace...")
        result = self.run_command(
            ['kubectl', 'create', 'namespace', self.namespace],
            check=False
        )
        
        # Deploy from YAML
        print("📦 Deploying resources...")
        yaml_file = self.project_root / 'k8s-deployment.yaml'
        result = self.run_command(['kubectl', 'apply', '-f', str(yaml_file)])
        
        if result['success']:
            print("✅ Deployment successful!")
            self.show_status()
            return True
        else:
            print(f"❌ Deployment failed: {result['stderr']}")
            return False
    
    def show_status(self) -> None:
        """Show deployment status"""
        print("\n📊 Deployment Status:")
        print("=" * 50)
        
        # Namespaces
        print("\n🔹 Namespace:")
        result = self.run_command(['kubectl', 'get', 'namespace', self.namespace])
        print(result['stdout'])
        
        # Pods
        print("\n🔹 Pods:")
        result = self.run_command(['kubectl', 'get', 'pods', '-n', self.namespace])
        print(result['stdout'])
        
        # Services
        print("\n🔹 Services:")
        result = self.run_command(['kubectl', 'get', 'svc', '-n', self.namespace])
        print(result['stdout'])
        
        # PVCs
        print("\n🔹 Persistent Volumes:")
        result = self.run_command(['kubectl', 'get', 'pvc', '-n', self.namespace])
        print(result['stdout'])
    
    def logs(self, pod_name: str = 'pvbesscar-pipeline-0') -> None:
        """Show pod logs"""
        print(f"\n📋 Logs for {pod_name}:")
        result = self.run_command(
            ['kubectl', 'logs', '-f', pod_name, '-n', self.namespace],
            check=False
        )
        print(result['stdout'])
    
    def describe(self, resource_type: str = 'pod', resource_name: str = '') -> None:
        """Describe resource"""
        cmd = ['kubectl', 'describe', resource_type, '-n', self.namespace]
        if resource_name:
            cmd.append(resource_name)
        
        result = self.run_command(cmd)
        print(result['stdout'])
    
    def exec_command(self, pod_name: str, command: str) -> None:
        """Execute command in pod"""
        cmd = ['kubectl', 'exec', '-it', pod_name, '-n', self.namespace, '--', 'sh', '-c', command]
        subprocess.run(cmd)
    
    def port_forward(self, service_name: str, local_port: int, remote_port: int) -> None:
        """Port forward to service"""
        print(f"\n🔌 Port forwarding {service_name}:")
        print(f"   Local:  http://localhost:{local_port}")
        print(f"   Remote: {service_name}:{remote_port}")
        print("   Press Ctrl+C to stop\n")
        
        cmd = [
            'kubectl', 'port-forward',
            f'svc/{service_name}',
            f'{local_port}:{remote_port}',
            '-n', self.namespace
        ]
        subprocess.run(cmd)
    
    def scale(self, replicas: int) -> None:
        """Scale deployment"""
        print(f"\n📈 Scaling pvbesscar-pipeline to {replicas} replicas...")
        result = self.run_command([
            'kubectl', 'scale', 'deployment', 'pvbesscar-pipeline',
            '--replicas', str(replicas),
            '-n', self.namespace
        ])
        
        if result['success']:
            print(f"✅ Scaled to {replicas} replicas")
            self.show_status()
        else:
            print(f"❌ Scaling failed: {result['stderr']}")
    
    def delete(self) -> None:
        """Delete deployment"""
        print("\n⚠️  Deleting PVBESSCAR deployment...")
        result = self.run_command([
            'kubectl', 'delete', 'namespace', self.namespace
        ], check=False)
        
        if result['success']:
            print("✅ Deployment deleted")
        else:
            print(f"❌ Deletion failed: {result['stderr']}")
    
    def mongo_shell(self) -> None:
        """Connect to MongoDB"""
        print("\n🍃 Connecting to MongoDB...")
        mongodb_pod = f"{self.namespace}-mongodb-0"
        
        cmd = [
            'kubectl', 'exec', '-it', mongodb_pod,
            '-n', self.namespace,
            '--', 'mongosh',
            '--username', 'admin',
            '--password', 'pvbesscar2026',
            '--authenticationDatabase', 'admin'
        ]
        subprocess.run(cmd)
    
    def mongodb_status(self) -> None:
        """Check MongoDB status"""
        print("\n🍃 MongoDB Status:")
        mongodb_pod = f"{self.namespace}-mongodb-0"
        
        cmd = [
            'kubectl', 'exec', mongodb_pod,
            '-n', self.namespace,
            '--', 'mongosh',
            '--username', 'admin',
            '--password', 'pvbesscar2026',
            '--authenticationDatabase', 'admin',
            '--eval', 'db.adminCommand("ping")'
        ]
        
        result = self.run_command(cmd)
        print(result['stdout'])

def main():
    """Main CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PVBESSCAR Kubernetes Manager')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Deploy
    subparsers.add_parser('deploy', help='Deploy to Kubernetes')
    
    # Status
    subparsers.add_parser('status', help='Show deployment status')
    
    # Logs
    logs_parser = subparsers.add_parser('logs', help='Show pod logs')
    logs_parser.add_argument('--pod', default='pvbesscar-pipeline-0')
    
    # Port forward
    forward_parser = subparsers.add_parser('forward', help='Port forward')
    forward_parser.add_argument('service', choices=['web', 'jupyter', 'mongodb'])
    
    # Scale
    scale_parser = subparsers.add_parser('scale', help='Scale deployment')
    scale_parser.add_argument('replicas', type=int)
    
    # MongoDB
    mongo_parser = subparsers.add_parser('mongo', help='MongoDB commands')
    mongo_parser.add_argument('command', choices=['shell', 'status'])
    
    # Delete
    subparsers.add_parser('delete', help='Delete deployment')
    
    args = parser.parse_args()
    manager = K8sManager()
    
    if args.command == 'deploy':
        manager.deploy()
    elif args.command == 'status':
        manager.show_status()
    elif args.command == 'logs':
        manager.logs(args.pod)
    elif args.command == 'forward':
        if args.service == 'web':
            manager.port_forward('pvbesscar-pipeline', 5000, 5000)
        elif args.service == 'jupyter':
            manager.port_forward('pvbesscar-pipeline', 8888, 8888)
        elif args.service == 'mongodb':
            manager.port_forward('mongodb', 27017, 27017)
    elif args.command == 'scale':
        manager.scale(args.replicas)
    elif args.command == 'mongo':
        if args.command_sub == 'shell':
            manager.mongo_shell()
        else:
            manager.mongodb_status()
    elif args.command == 'delete':
        manager.delete()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
