#!/usr/bin/env python3
"""
Script de validación: Verifica que todas las librerías instaladas
estén correctamente integradas en requirements.txt y requirements-training.txt
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def normalize_package_name(name: str) -> str:
    """Normaliza nombres de paquetes (guiones a guiones bajos)"""
    return name.lower().replace("-", "_")


def get_installed_packages() -> dict[str, str]:
    """Obtiene todas las librerías instaladas con sus versiones"""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    )
    packages = json.loads(result.stdout)
    return {pkg["name"].lower(): pkg["version"] for pkg in packages}


def parse_requirements_file(file_path: Path) -> dict[str, str]:
    """Parsea un archivo requirements y extrae nombre==version"""
    requirements = {}
    with open(file_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            # Ignorar comentarios y líneas vacías
            if not line or line.startswith("#"):
                continue
            # Extraer nombre y versión
            if "==" in line:
                name, version = line.split("==", 1)
                requirements[name.lower().strip()] = version.strip()
    return requirements


def main() -> None:
    """Valida integración de requirements"""
    workspace_root = Path(__file__).parent

    print("=" * 80)
    print("✓ VALIDACIÓN DE REQUIREMENTS INTEGRADOS")
    print("=" * 80)

    # 1. Obtener librerías instaladas
    print("\n📦 Obteniendo librerías instaladas...")
    installed = get_installed_packages()
    # Normalizar nombres de paquetes instalados
    installed_normalized = {normalize_package_name(k): v for k, v in installed.items()}
    print(f"   ✓ {len(installed)} librerías instaladas encontradas")

    # 2. Parsear requirements.txt
    print("\n📄 Parseando requirements.txt...")
    req_base_path = workspace_root / "requirements.txt"
    req_base = parse_requirements_file(req_base_path)
    # Normalizar nombres en requirements.txt
    req_base_normalized = {normalize_package_name(k): v for k, v in req_base.items()}
    print(f"   ✓ {len(req_base)} librerías en requirements.txt")

    # 3. Parsear requirements-training.txt
    print("\n📄 Parseando requirements-training.txt...")
    req_training_path = workspace_root / "requirements-training.txt"
    req_training = parse_requirements_file(req_training_path)
    # Normalizar nombres en requirements-training.txt
    req_training_normalized = {
        normalize_package_name(k): v for k, v in req_training.items()
    }
    print(f"   ✓ {len(req_training)} librerías en requirements-training.txt")

    # 4. Validar que todas las instaladas estén en uno de los requirements
    print("\n🔍 VALIDACIÓN: Librerías instaladas vs Requirements")
    print("-" * 80)

    missing_in_base: set[str] = set()
    mismatched_versions: list[tuple[str, str, str, str]] = []

    for pkg_name_norm, pkg_version in installed_normalized.items():
        # Excluir paquetes internos/editable
        if pkg_name_norm in ["pvbesscar", "iquitos_citylearn"]:
            if pkg_name_norm == "iquitos_citylearn":
                # Verificar que esté en requirements.txt
                if pkg_name_norm not in req_base_normalized:
                    print(f"   ⚠️  FALTA en requirements.txt: {pkg_name_norm}")
                    missing_in_base.add(pkg_name_norm)
            continue

        # Verificar en requirements.txt
        if (
            pkg_name_norm not in req_base_normalized
            and pkg_name_norm not in req_training_normalized
        ):
            missing_in_base.add(pkg_name_norm)
            print(f"   ❌ NO ENCONTRADO en ningún requirements: {pkg_name_norm}=={pkg_version}")
        else:
            # Verificar coincidencia de versión
            if pkg_name_norm in req_base_normalized:
                if req_base_normalized[pkg_name_norm] != pkg_version:
                    mismatched_versions.append(
                        (
                            pkg_name_norm,
                            f"requirements.txt",
                            req_base_normalized[pkg_name_norm],
                            pkg_version,
                        )
                    )
            elif pkg_name_norm in req_training_normalized:
                if req_training_normalized[pkg_name_norm] != pkg_version:
                    mismatched_versions.append(
                        (
                            pkg_name_norm,
                            f"requirements-training.txt",
                            req_training_normalized[pkg_name_norm],
                            pkg_version,
                        )
                    )

    # 5. Resumen de validación
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE VALIDACIÓN")
    print("=" * 80)

    print(f"\n✓ Librerías instaladas: {len(installed)}")
    print(f"✓ En requirements.txt: {len(req_base)}")
    print(f"✓ En requirements-training.txt: {len(req_training)}")

    if missing_in_base:
        print(f"\n⚠️  FALTANTES: {len(missing_in_base)} librerías no están en requirements")
        for pkg in sorted(missing_in_base):
            version = installed_normalized[pkg]
            print(f"   • {pkg}=={version}")
    else:
        print("\n✅ Todas las librerías instaladas están en requirements")

    if mismatched_versions:
        print(f"\n⚠️  VERSIONES DESAJUSTADAS: {len(mismatched_versions)} librerías")
        for pkg_name, file_name, req_version, inst_version in mismatched_versions:
            print(
                f"   • {pkg_name}: {file_name} tiene {req_version}, "
                f"instalado {inst_version}"
            )
    else:
        print("\n✅ Todas las versiones coinciden correctamente")

    # 6. Categorías detectadas
    print("\n" + "=" * 80)
    print("📋 CATEGORÍAS EN requirements.txt")
    print("=" * 80)

    categories: dict[str, list[str]] = {}
    current_category = "Otros"

    with open(req_base_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("# "):
                if "=" in line and line.count("=") > 2:
                    current_category = line.strip("# ").replace("=", "").strip()
                    categories[current_category] = []
            elif "==" in line:
                name = line.split("==")[0].strip()
                if current_category not in categories:
                    categories[current_category] = []
                categories[current_category].append(name)

    for cat in sorted(categories.keys()):
        if categories[cat]:
            print(f"\n{cat}: ({len(categories[cat])} librerías)")
            # Mostrar primeras 5
            for pkg in sorted(categories[cat])[:5]:
                print(f"  • {pkg}")
            if len(categories[cat]) > 5:
                print(f"  • ... y {len(categories[cat]) - 5} más")

    # 7. Status final
    print("\n" + "=" * 80)
    if not missing_in_base and not mismatched_versions:
        print("✅ VALIDACIÓN EXITOSA: Todos los requirements están integrados correctamente")
        print(f"   • requirements.txt: {len(req_base)} librerías")
        print(f"   • requirements-training.txt: {len(req_training)} librerías")
        return_code = 0
    else:
        print("⚠️  ADVERTENCIAS: Revisar discrepancias arriba")
        return_code = 1

    print("=" * 80 + "\n")
    sys.exit(return_code)


if __name__ == "__main__":
    main()
