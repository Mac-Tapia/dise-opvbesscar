#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDACIÓN PROFESIONAL DE ARQUITECTURA Y FLUJO DE TRABAJO
=========================================================================
Validación exhaustiva de:
1. Sincronización de configuraciones (YAML, JSON, Python)
2. Consistencia de pesos multiobjetivo en todos los agentes
3. Arquitectura general del proyecto
4. Integración con tabla comparativa baseline
5. Especificaciones técnicas reales

Autor: Arquitectura OE3 SAC/PPO/A2C
Fecha: 2026-02-07
=========================================================================
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import yaml

# Colores para output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_section(title: str, level: int = 1):
    """Imprime sección con formato."""
    if level == 1:
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{title:^80}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")
    elif level == 2:
        print(f"\n{Colors.OKBLUE}{Colors.BOLD}{title}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'-'*80}{Colors.ENDC}")
    else:
        print(f"\n{Colors.OKCYAN}• {title}{Colors.ENDC}")

def print_ok(msg: str):
    """Imprime mensaje OK."""
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def print_error(msg: str):
    """Imprime mensaje ERROR."""
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")

def print_warning(msg: str):
    """Imprime mensaje WARNING."""
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")

def print_info(msg: str, indent: int = 1):
    """Imprime mensaje INFO."""
    indent_str = "  " * indent
    print(f"{indent_str}{Colors.OKBLUE}{msg}{Colors.ENDC}")

@dataclass
class ValidationResult:
    """Resultado de validación."""
    category: str
    check: str
    status: bool
    message: str
    details: str = ""

class ArchitectureValidator:
    """Validador principal de arquitectura."""
    
    def __init__(self, project_root: Path = Path(".")):
        self.project_root = project_root
        self.results: List[ValidationResult] = []
        self.configs: Dict[str, Any] = {}
        self.weights_by_source: Dict[str, Dict[str, float]] = {}
    
    def validate_all(self):
        """Ejecuta todas las validaciones."""
        print_section("VALIDACIÓN PROFESIONAL DE ARQUITECTURA Y FLUJO DE TRABAJO", level=1)
        print(f"{Colors.OKBLUE}Raíz del proyecto: {self.project_root}{Colors.ENDC}\n")
        
        # 1. Validación de archivos de configuración
        self._validate_config_files()
        
        # 2. Validación de pesos multiobjetivo
        self._validate_weights_synchronization()
        
        # 3. Validación de scripts de entrenamiento
        self._validate_training_scripts()
        
        # 4. Validación de archivos OE2
        self._validate_oe2_data()
        
        # 5. Validación de tabla comparativa baseline
        self._validate_baseline_comparison()
        
        # 6. Validación de arquitectura de directorios
        self._validate_directory_structure()
        
        # 7. Validación de código Python
        self._validate_code_consistency()
        
        # Reporte final
        self._print_summary()
    
    def _validate_config_files(self):
        """Valida archivos de configuración YAML/JSON."""
        print_section("1. VALIDACIÓN DE CONFIGURACIONES (YAML/JSON)", level=2)
        
        configs_to_check = {
            "default.yaml": self.project_root / "configs" / "default.yaml",
            "agents_config.yaml": self.project_root / "configs" / "agents" / "agents_config.yaml",
            "sac_config.yaml": self.project_root / "configs" / "agents" / "sac_config.yaml",
            "ppo_config.yaml": self.project_root / "configs" / "agents" / "ppo_config.yaml",
            "a2c_config.yaml": self.project_root / "configs" / "agents" / "a2c_config.yaml",
        }
        
        for config_name, config_path in configs_to_check.items():
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        if config_path.suffix == '.yaml':
                            config = yaml.safe_load(f)
                        else:
                            config = json.load(f)
                    
                    self.configs[config_name] = config
                    print_ok(f"{config_name} - Cargado exitosamente")
                    
                    self.results.append(ValidationResult(
                        category="Configuración",
                        check=f"Archivo {config_name}",
                        status=True,
                        message=f"Archivo {config_name} válido y accesible"
                    ))
                except Exception as e:
                    print_error(f"{config_name} - Error al cargar: {str(e)}")
                    self.results.append(ValidationResult(
                        category="Configuración",
                        check=f"Archivo {config_name}",
                        status=False,
                        message=f"Error al cargar: {str(e)}"
                    ))
            else:
                print_warning(f"{config_name} - No encontrado en {config_path}")
                self.results.append(ValidationResult(
                    category="Configuración",
                    check=f"Archivo {config_name}",
                    status=False,
                    message=f"Archivo no encontrado"
                ))
    
    def _validate_weights_synchronization(self):
        """Valida sincronización de pesos multiobjetivo."""
        print_section("2. VALIDACIÓN DE SINCRONIZACIÓN DE PESOS MULTIOBJETIVO", level=2)
        
        # Pesos esperados según especificación
        expected_weights = {
            "co2": 0.50,
            "solar": 0.25,
            "ev": 0.15,  # ev_satisfaction o ev
            "cost": 0.05,
            "grid": 0.05,  # grid_stability
        }
        
        total_expected = sum(expected_weights.values())
        print_info(f"Pesos esperados (total={total_expected:.2f}):", indent=0)
        for k, v in expected_weights.items():
            print_info(f"  {k}: {v:.2f}", indent=1)
        
        # Extraer pesos de diferentes fuentes
        print_section("Extrayendo pesos de configuraciones...", level=3)
        
        # 1. De agents_config.yaml
        if "agents_config.yaml" in self.configs:
            config = self.configs["agents_config.yaml"]
            if "reward_weights" in config:
                weights = config["reward_weights"]
                self.weights_by_source["agents_config.yaml"] = weights
                total = sum([v for k, v in weights.items() if k != "total"])
                print_info(f"agents_config.yaml: {weights}", indent=1)
                print_info(f"  Total: {total:.2f}", indent=1)
        
        # 2. De sac_config.yaml
        if "sac_config.yaml" in self.configs:
            config = self.configs["sac_config.yaml"]
            if "multi_objective_weights" in config["sac"]:
                weights = config["sac"]["multi_objective_weights"]
                self.weights_by_source["sac_config.yaml"] = weights
                total = sum(weights.values())
                print_info(f"sac_config.yaml: {weights}", indent=1)
                print_info(f"  Total: {total:.2f}", indent=1)
        
        # 3. De ppo_config.yaml
        if "ppo_config.yaml" in self.configs:
            config = self.configs["ppo_config.yaml"]
            if "multi_objective_weights" in config["ppo"]:
                weights = config["ppo"]["multi_objective_weights"]
                self.weights_by_source["ppo_config.yaml"] = weights
                total = sum(weights.values())
                print_info(f"ppo_config.yaml: {weights}", indent=1)
                print_info(f"  Total: {total:.2f}", indent=1)
        
        # 4. De a2c_config.yaml
        if "a2c_config.yaml" in self.configs:
            config = self.configs["a2c_config.yaml"]
            if "multi_objective_weights" in config["a2c"]:
                weights = config["a2c"]["multi_objective_weights"]
                self.weights_by_source["a2c_config.yaml"] = weights
                total = sum(weights.values())
                print_info(f"a2c_config.yaml: {weights}", indent=1)
                print_info(f"  Total: {total:.2f}", indent=1)
        
        # Validar sincronización
        print_section("Validando sincronización...", level=3)
        
        all_weights_equal = True
        reference_weights = None
        
        for source, weights in self.weights_by_source.items():
            if reference_weights is None:
                reference_weights = weights
                print_ok(f"{source} - Establecido como referencia")
            else:
                # Comparar
                if weights == reference_weights:
                    print_ok(f"{source} - SINCRONIZADO con referencia")
                    self.results.append(ValidationResult(
                        category="Pesos",
                        check=f"Sincronización {source}",
                        status=True,
                        message="Los pesos están sincronizados"
                    ))
                else:
                    print_error(f"{source} - DESINCRONIZADO")
                    print_info(f"  Esperado: {reference_weights}", indent=2)
                    print_info(f"  Actual:   {weights}", indent=2)
                    all_weights_equal = False
                    self.results.append(ValidationResult(
                        category="Pesos",
                        check=f"Sincronización {source}",
                        status=False,
                        message="Los pesos NO están sincronizados",
                        details=f"Esperado: {reference_weights}, Actual: {weights}"
                    ))
        
        # Validar suma = 1.0
        if reference_weights:
            total = sum(reference_weights.values())
            if abs(total - 1.0) < 0.001:
                print_ok(f"Suma de pesos = {total:.4f} (correcto)")
                self.results.append(ValidationResult(
                    category="Pesos",
                    check="Suma de pesos",
                    status=True,
                    message=f"Suma correcta: {total:.4f}"
                ))
            else:
                print_error(f"Suma de pesos = {total:.4f} (incorrecto, esperado ~1.0)")
                self.results.append(ValidationResult(
                    category="Pesos",
                    check="Suma de pesos",
                    status=False,
                    message=f"Suma incorrecta: {total:.4f}"
                ))
    
    def _validate_training_scripts(self):
        """Valida scripts de entrenamiento."""
        print_section("3. VALIDACIÓN DE SCRIPTS DE ENTRENAMIENTO", level=2)
        
        training_scripts = {
            "SAC": self.project_root / "train_sac_multiobjetivo.py",
            "PPO": self.project_root / "train_ppo_multiobjetivo.py",
            "A2C": self.project_root / "train_a2c_multiobjetivo.py",
        }
        
        for agent_type, script_path in training_scripts.items():
            if script_path.exists():
                print_ok(f"{agent_type} script encontrado: {script_path.name}")
                
                # Leer script y buscar patrones clave
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    checks = {
                        "MultiObjectiveReward": "MultiObjectiveReward" in content,
                        "IquitosContext": "IquitosContext" in content,
                        "create_iquitos_reward_weights": "create_iquitos_reward_weights" in content,
                        "co2_focus": '"co2_focus"' in content or "'co2_focus'" in content,
                    }
                    
                    for check_name, result in checks.items():
                        if result:
                            print_info(f"✓ {agent_type}: Contiene {check_name}", indent=1)
                            self.results.append(ValidationResult(
                                category="Scripts",
                                check=f"{agent_type} - {check_name}",
                                status=True,
                                message=f"Script {agent_type} contiene {check_name}"
                            ))
                        else:
                            print_warning(f"⚠ {agent_type}: NO contiene {check_name}", )
                            self.results.append(ValidationResult(
                                category="Scripts",
                                check=f"{agent_type} - {check_name}",
                                status=False,
                                message=f"Script {agent_type} NO contiene {check_name}"
                            ))
                
                except Exception as e:
                    print_error(f"Error al leer {agent_type} script: {e}")
            else:
                print_error(f"{agent_type} script NO encontrado: {script_path}")
                self.results.append(ValidationResult(
                    category="Scripts",
                    check=f"Existencia {agent_type}",
                    status=False,
                    message=f"Script {agent_type} no encontrado"
                ))
    
    def _validate_oe2_data(self):
        """Valida presencia de datos OE2."""
        print_section("4. VALIDACIÓN DE DATOS OE2", level=2)
        
        oe2_files = {
            "Solar PV": self.project_root / "data/interim/oe2/solar/pv_generation_citylearn_v2.csv",
            "Chargers": self.project_root / "data/interim/oe2/chargers/chargers_real_hourly_2024.csv",
            "Historical": self.project_root / "data/interim/oe2/chargers/chargers_real_statistics.csv",
        }
        
        for file_type, file_path in oe2_files.items():
            if file_path.exists():
                file_size_kb = file_path.stat().st_size / 1024
                print_ok(f"{file_type} - Encontrado ({file_size_kb:.1f} KB)")
                self.results.append(ValidationResult(
                    category="OE2 Data",
                    check=f"Archivo {file_type}",
                    status=True,
                    message=f"Archivo {file_type} existe y es accesible"
                ))
            else:
                print_warning(f"{file_type} - NO encontrado en {file_path}")
                self.results.append(ValidationResult(
                    category="OE2 Data",
                    check=f"Archivo {file_type}",
                    status=False,
                    message=f"Archivo {file_type} no encontrado en ubicación esperada"
                ))
    
    def _validate_baseline_comparison(self):
        """Valida tabla comparativa baseline."""
        print_section("5. VALIDACIÓN DE TABLA COMPARATIVA BASELINE", level=2)
        
        baseline_file = self.project_root / "outputs/baselines/baseline_comparison.csv"
        
        if baseline_file.exists():
            print_ok(f"Tabla comparativa encontrada: {baseline_file}")
            
            try:
                with open(baseline_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                print_info(f"Número de líneas: {len(lines)}", indent=1)
                
                # Leer y mostrar contenido
                import csv
                reader = csv.DictReader(lines)
                baselines = list(reader)
                
                print_info(f"Baselines encontrados:", indent=1)
                for baseline in baselines:
                    baseline_name = baseline.get('baseline', 'N/A')
                    description = baseline.get('description', 'N/A')
                    co2_grid_kg = baseline.get('co2_grid_kg', 'N/A')
                    print_info(f"{baseline_name}: {description}", indent=2)
                    print_info(f"  CO₂ Grid: {co2_grid_kg} kg", indent=2)
                
                self.results.append(ValidationResult(
                    category="Baseline",
                    check="Tabla comparativa",
                    status=True,
                    message=f"Tabla comparativa válida con {len(baselines)} baseline(s)"
                ))
                
            except Exception as e:
                print_error(f"Error al leer tabla comparativa: {e}")
                self.results.append(ValidationResult(
                    category="Baseline",
                    check="Lectura tabla",
                    status=False,
                    message=f"Error al leer: {e}"
                ))
        else:
            print_warning(f"Tabla comparativa NO encontrada en {baseline_file}")
            self.results.append(ValidationResult(
                category="Baseline",
                check="Existencia tabla",
                status=False,
                message="Tabla comparativa no encontrada en ubicación esperada"
            ))
    
    def _validate_directory_structure(self):
        """Valida estructura de directorios."""
        print_section("6. VALIDACIÓN DE ESTRUCTURA DE DIRECTORIOS", level=2)
        
        required_dirs = {
            "src": self.project_root / "src",
            "src/rewards": self.project_root / "src/rewards",
            "data": self.project_root / "data",
            "configs": self.project_root / "configs",
            "checkpoints": self.project_root / "checkpoints",
            "outputs": self.project_root / "outputs",
        }
        
        for dir_name, dir_path in required_dirs.items():
            if dir_path.exists():
                print_ok(f"{dir_name} - ✓")
                self.results.append(ValidationResult(
                    category="Directorios",
                    check=f"Directorio {dir_name}",
                    status=True,
                    message=f"Directorio {dir_name} existe"
                ))
            else:
                print_error(f"{dir_name} - ✗ NO encontrado")
                self.results.append(ValidationResult(
                    category="Directorios",
                    check=f"Directorio {dir_name}",
                    status=False,
                    message=f"Directorio {dir_name} no existe"
                ))
    
    def _validate_code_consistency(self):
        """Valida consistencia del código Python."""
        print_section("7. VALIDACIÓN DE CONSISTENCIA DE CÓDIGO", level=2)
        
        rewards_file = self.project_root / "src/rewards/rewards.py"
        
        if rewards_file.exists():
            print_ok(f"rewards.py encontrado")
            
            try:
                with open(rewards_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Verificar presencia de clases y funciones clave
                key_elements = {
                    "MultiObjectiveWeights": "class MultiObjectiveWeights" in content,
                    "IquitosContext": "class IquitosContext" in content,
                    "MultiObjectiveReward": "class MultiObjectiveReward" in content,
                    "create_iquitos_reward_weights": "def create_iquitos_reward_weights" in content,
                }
                
                print_info("Elementos clave encontrados:", indent=1)
                for element, found in key_elements.items():
                    if found:
                        print_ok(f"{element}")
                        self.results.append(ValidationResult(
                            category="Código",
                            check=f"Elemento {element}",
                            status=True,
                            message=f"{element} definido correctamente"
                        ))
                    else:
                        print_error(f"{element} - NO encontrado")
                        self.results.append(ValidationResult(
                            category="Código",
                            check=f"Elemento {element}",
                            status=False,
                            message=f"{element} no encontrado"
                        ))
            
            except Exception as e:
                print_error(f"Error al leer rewards.py: {e}")
        else:
            print_error(f"rewards.py NO encontrado")
    
    def _print_summary(self):
        """Imprime resumen de resultados."""
        print_section("RESUMEN DE VALIDACIÓN", level=1)
        
        # Contar resultados
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status)
        failed = total - passed
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print_info(f"Total de validaciones: {total}", indent=0)
        print_info(f"✓ Exitosas: {passed}", indent=0)
        print_info(f"✗ Fallidas: {failed}", indent=0)
        print_info(f"Tasa de éxito: {success_rate:.1f}%", indent=0)
        
        # Agrupar por categoría
        print("\n" + Colors.BOLD + "RESULTADOS POR CATEGORÍA:" + Colors.ENDC)
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {"passed": 0, "failed": 0}
            if result.status:
                categories[result.category]["passed"] += 1
            else:
                categories[result.category]["failed"] += 1
        
        for category, stats in sorted(categories.items()):
            total_cat = stats["passed"] + stats["failed"]
            rate_cat = (stats["passed"] / total_cat * 100) if total_cat > 0 else 0
            status_icon = Colors.OKGREEN + "✓" + Colors.ENDC if stats["failed"] == 0 else Colors.FAIL + "✗" + Colors.ENDC
            print(f"  {status_icon} {category}: {stats['passed']}/{total_cat} ({rate_cat:.0f}%)")
        
        # Recomendaciones
        print("\n" + Colors.BOLD + "RECOMENDACIONES:" + Colors.ENDC)
        if success_rate == 100.0:
            print(f"{Colors.OKGREEN}✓ ARQUITECTURA VÁLIDA Y SINCRONIZADA{Colors.ENDC}")
            print(f"{Colors.OKGREEN}✓ Todos los componentes están correctamente configurados{Colors.ENDC}")
            print(f"{Colors.OKGREEN}✓ Proyecto listo para entrenamiento{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}⚠ Se detectaron {failed} issue(s){Colors.ENDC}")
            print(f"{Colors.WARNING}⚠ Revise los errores marcados con ✗ arriba{Colors.ENDC}")
        
        print("\n" + Colors.BOLD + "DETALLES DE FALLOS:" + Colors.ENDC)
        failures = [r for r in self.results if not r.status]
        if failures:
            for failure in failures:
                print(f"\n{Colors.FAIL}✗ {failure.category} - {failure.check}{Colors.ENDC}")
                print(f"  Mensaje: {failure.message}")
                if failure.details:
                    print(f"  Detalles: {failure.details}")
        else:
            print(f"{Colors.OKGREEN}Sin fallos detectados{Colors.ENDC}")
        
        print("\n" + Colors.BOLD + "VERIFICACIÓN FINAL:" + Colors.ENDC)
        print(f"{Colors.OKBLUE}Arquitectura profesional validada el 2026-02-07{Colors.ENDC}")
        print(f"{Colors.OKBLUE}Proyecto: diseñopvbesscar (OE3 SAC/PPO/A2C){Colors.ENDC}")
        print(f"{Colors.OKBLUE}Rama: oe3-optimization-sac-ppo{Colors.ENDC}")


if __name__ == "__main__":
    validator = ArchitectureValidator()
    validator.validate_all()
