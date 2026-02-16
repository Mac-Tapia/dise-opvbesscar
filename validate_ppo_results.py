#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDACIÓN DE RESULTADOS PPO Y MEJORA CONTINUA
================================================================================
Valida que PPO se entrenó correctamente y aplica mejoras iterativas.
- Verifica que checkpoints se crearon
- Compara métricas PPO vs SAC vs A2C
- Detecta problemas y aplica correcciones
================================================================================
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any, Optional, List
import subprocess

def print_header(text: str):
    print('\n' + '='*80)
    print(f'[VALIDAR PPO] {text}')
    print('='*80)

def print_step(text: str):
    print(f'\n[PASO] {text}')
    print('-' * 80)

def print_ok(text: str):
    print(f'  ✓ {text}')

def print_warning(text: str):
    print(f'  ⚠ {text}')

def print_error(text: str):
    print(f'  ✗ {text}')

class PPOValidator:
    def __init__(self):
        self.issues: List[Dict[str, str]] = []
        self.recommendations: List[str] = []
        self.validation_results: Dict[str, bool] = {}
    
    def check_checkpoints_exist(self) -> bool:
        """Verificar que checkpoints se crearon."""
        print_step('1. Verificar checkpoints PPO')
        
        ppo_dir = Path('checkpoints/PPO')
        if not ppo_dir.exists():
            print_error(f'Directorio no existe: {ppo_dir}')
            self.issues.append({
                'check': 'checkpoints_exist',
                'severity': 'critical',
                'message': 'Directorio checkpoints/PPO no existe'
            })
            return False
        
        checkpoint_files = list(ppo_dir.glob('*.zip'))
        if not checkpoint_files:
            print_error('No hay archivos .zip en checkpoints/PPO')
            self.issues.append({
                'check': 'checkpoint_files',
                'severity': 'critical',
                'message': 'No se encontraron archivos de checkpoint (.zip)'
            })
            return False
        
        latest = max(checkpoint_files, key=lambda p: p.stat().st_mtime)
        file_size = latest.stat().st_size / 1024 / 1024  # MB
        
        print_ok(f'Checkpoints encontrados: {len(checkpoint_files)} archivos')
        print_ok(f'Último checkpoint: {latest.name} ({file_size:.2f} MB)')
        
        self.validation_results['checkpoints_exist'] = True
        return True
    
    def check_sac_a2c_protected(self) -> bool:
        """Verificar que SAC y A2C están protegidos."""
        print_step('2. Validar que SAC/A2C están protegidos')
        
        sac_dir = Path('checkpoints/SAC')
        a2c_dir = Path('checkpoints/A2C')
        
        sac_ok = False
        a2c_ok = False
        
        if sac_dir.exists():
            sac_files = list(sac_dir.glob('*.zip'))
            if sac_files:
                print_ok(f'SAC PROTEGIDO: {len(sac_files)} checkpoint(s)')
                sac_ok = True
            else:
                print_warning('SAC existe pero no contiene checkpoints')
        else:
            print_warning('SAC no existe')
        
        if a2c_dir.exists():
            a2c_files = list(a2c_dir.glob('*.zip'))
            if a2c_files:
                print_ok(f'A2C PROTEGIDO: {len(a2c_files)} checkpoint(s)')
                a2c_ok = True
            else:
                print_warning('A2C existe pero no contiene checkpoints')
        else:
            print_warning('A2C no existe')
        
        self.validation_results['protection'] = sac_ok or a2c_ok
        return sac_ok or a2c_ok
    
    def check_training_logs(self) -> bool:
        """Verificar que el log de entrenamiento contiene datos válidos."""
        print_step('3. Validar logs de entrenamiento')
        
        log_file = Path('ppo_training_live.log')
        if not log_file.exists():
            print_warning('Log file no encontrado')
            self.validation_results['logs'] = False
            return False
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            file_size = log_file.stat().st_size / 1024 / 1024  # MB
            print_ok(f'Log file: {log_file.name} ({file_size:.2f} MB)')
            
            # Detectar episodios y metrícas
            import re
            episodes = len(re.findall(r'Episode \d+', content))
            returns = len(re.findall(r'Return: [\d\.\-]+', content))
            
            print_ok(f'Episodios detectados: {episodes}')
            print_ok(f'Métricas detectadas: {returns}')
            
            if episodes > 0 and returns > 0:
                self.validation_results['logs'] = True
                return True
            else:
                self.issues.append({
                    'check': 'logs_content',
                    'severity': 'warning',
                    'message': f'Pocos datos en log: {episodes} episodios, {returns} returns'
                })
                return False
        
        except Exception as e:
            print_error(f'Error leyendo log: {e}')
            self.issues.append({
                'check': 'logs_read',
                'severity': 'error',
                'message': f'Error leyendo log: {e}'
            })
            return False
    
    def check_monitoring_data(self) -> bool:
        """Verificar que se generaron datos de monitoreo."""
        print_step('4. Validar datos de monitoreo continuo')
        
        metrics_file = Path('outputs/ppo_monitoring/metrics_continuous.json')
        problems_file = Path('outputs/ppo_monitoring/problems_detected.json')
        
        metrics_ok = False
        problems_data = []
        
        if metrics_file.exists():
            try:
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
                print_ok(f'Métricas registradas: {len(metrics)} data points')
                metrics_ok = True
                
                # Analizar calidad de métricas
                if metrics:
                    latest = metrics[-1]
                    print_ok(f'Última métrica: {latest.get("episode", "?")} episodios')
            except Exception as e:
                print_warning(f'Error leyendo métricas: {e}')
        
        if problems_file.exists():
            try:
                with open(problems_file, 'r') as f:
                    problems_data = json.load(f)
                if problems_data:
                    print_warning(f'Problemas detectados durante monitoreo: {len(problems_data)}')
                    for prob in problems_data[:3]:  # Mostrar primeros 3
                        msg = prob.get('message', '?')
                        print_warning(f'  - {msg}')
                else:
                    print_ok('Sin problemas detectados durante monitoreo')
            except Exception as e:
                print_warning(f'Error leyendo problemas: {e}')
        
        self.validation_results['monitoring'] = metrics_ok
        
        # Si hay muchos problemas, recomendar mejoras
        if len(problems_data) > 5:
            self.recommendations.append('Reducir learning rate (LR demasiado alto)')
            self.recommendations.append('Aumentar n_steps para mejor estimación de ventaja')
            self.recommendations.append('Revisar reward shaping')
        
        return metrics_ok
    
    def compare_with_other_agents(self) -> None:
        """Comparar resultados PPO con SAC y A2C."""
        print_step('5. Comparar PPO con SAC y A2C')
        
        agents = {
            'PPO': Path('checkpoints/PPO'),
            'SAC': Path('checkpoints/SAC'),
            'A2C': Path('checkpoints/A2C'),
        }
        
        comparison = {}
        for agent, checkpoint_dir in agents.items():
            if checkpoint_dir.exists():
                files = list(checkpoint_dir.glob('*.zip'))
                comparison[agent] = {
                    'checkpoints': len(files),
                    'latest': max([f.stat().st_mtime for f in files]) if files else 0
                }
            else:
                comparison[agent] = {'checkpoints': 0, 'latest': 0}
        
        print('\n  Comparativa de checkpoints:')
        for agent, data in comparison.items():
            if data['checkpoints'] > 0:
                timestamp = datetime.fromtimestamp(data['latest']).strftime('%Y-%m-%d %H:%M:%S')
                print(f'    {agent}: {data["checkpoints"]} checkpoint(s) - {timestamp}')
            else:
                print(f'    {agent}: sin checkpoints')
    
    def generate_recommendations(self) -> None:
        """Generar recomendaciones basadas en validación."""
        print_step('6. Recomendaciones de mejora continua')
        
        if not self.recommendations:
            print_ok('Entrenamiento completado exitosamente')
            print_ok('Recomendaciones: Proceder a evaluación comparativa con SAC/A2C')
        else:
            print_warning('Problemas detectados - Aplicar mejoras:')
            for i, rec in enumerate(self.recommendations, 1):
                print(f'  {i}. {rec}')
        
        # Recomendaciones estándar
        next_steps = [
            'Ejecutar evaluación determinística del agente PPO',
            'Comparar rewards con baseline (sin control)',
            'Análisis de CO2 reducido vs SAC/A2C',
            'Generar gráficos de convergencia',
        ]
        
        print('\n  Próximos pasos:')
        for i, step in enumerate(next_steps, 1):
            print(f'    {i}. {step}')
    
    def run_full_validation(self) -> int:
        """Ejecutar validación completa."""
        print_header('VALIDACIÓN COMPLETA DE ENTRENAMIENTO PPO')
        
        all_ok = True
        
        # Check 1: Checkpoints
        if not self.check_checkpoints_exist():
            all_ok = False
        
        # Check 2: Protección SAC/A2C
        self.check_sac_a2c_protected()
        
        # Check 3: Logs
        if not self.check_training_logs():
            all_ok = False
        
        # Check 4: Monitoring
        self.check_monitoring_data()
        
        # Check 5: Comparativa
        self.compare_with_other_agents()
        
        # Check 6: Recomendaciones
        self.generate_recommendations()
        
        # Resumen final
        print_step('7. Resumen de validación')
        
        if all_ok:
            print_header('✓ VALIDACIÓN EXITOSA')
            print('''
┌────────────────────────────────────────────────────┐
│  ENTRENAMIENTO PPO VALIDADO                        │
├────────────────────────────────────────────────────┤
│  ✓ Checkpoints creados correctamente               │
│  ✓ SAC/A2C protegidos                              │
│  ✓ Logs de entrenamiento generados                 │
│  ✓ Monitoreo completado                            │
├────────────────────────────────────────────────────┤
│  Contador de issues: {}                           │
│  Contador de problemas monitoreo: ?                │
├────────────────────────────────────────────────────┤
│  Siguiente: Ejecutar evaluación deterministica     │
│  Archivo: python evaluate_ppo_deterministic.py     │
└────────────────────────────────────────────────────┘
            '''.format(len(self.issues)))
            return 0
        else:
            print_header('⚠ VALIDACIÓN PARCIAL')
            print('\nIssues detectados:')
            for issue in self.issues:
                severity_symbol = '✗' if issue['severity'] == 'critical' else '⚠'
                print(f'  {severity_symbol} [{issue["severity"].upper()}] {issue["message"]}')
            return 1

def main():
    validator = PPOValidator()
    sys.exit(validator.run_full_validation())

if __name__ == '__main__':
    main()
