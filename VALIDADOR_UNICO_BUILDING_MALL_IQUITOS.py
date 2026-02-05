#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VALIDADOR_UNICO_BUILDING_MALL_IQUITOS.py
==========================================

Verifica que SOLO se use 1 edificio (Mall_Iquitos) en todo el sistema.
Detecta cualquier intento de cargar múltiples edificios o archivos antiguos.

Ejecución:
  python VALIDADOR_UNICO_BUILDING_MALL_IQUITOS.py

Esperado:
  ✓ 1 edificio: Mall_Iquitos
  ✓ 128 cargadores
  ✓ NO Building_*.csv
  ✓ SOLO charger_simulation_*.csv
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any


class SingleBuildingValidator:
    """Validador que NO permite múltiples edificios en el dataset."""

    def __init__(self, root_dir: Path = Path(".")):
        self.root = Path(root_dir)
        self.citylearn_dir = self.root / "data" / "processed" / "citylearn" / "iquitos_ev_mall"
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    def run_all_checks(self):
        """Ejecutar todas las validaciones."""
        print("\n" + "="*80)
        print("VALIDADOR: ÚNICO BUILDING (MALL_IQUITOS)")
        print("="*80 + "\n")

        self._check_schema_json()
        self._check_no_building_csv()
        self._check_no_charger_old_format()
        self._check_no_washing_machines()
        self._check_no_alternate_schemas()
        self._check_charger_simulation_files()
        self._check_directory_file_count()
        self._summary()

    def _check_schema_json(self):
        """Verificar que schema.json SOLO contiene Mall_Iquitos."""
        print("[PASO 1] Validar schema.json")
        print("-" * 80)

        schema_file = self.citylearn_dir / "schema.json"
        if not schema_file.exists():
            self.errors.append(f"CRÍTICO: schema.json NO ENCONTRADO en {self.citylearn_dir}")
            print(f"  ❌ schema.json NOT FOUND")
            return

        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)
        except Exception as e:
            self.errors.append(f"ERROR al leer schema.json: {e}")
            print(f"  ❌ Error reading schema.json: {e}")
            return

        buildings = schema.get("buildings", {})
        num_buildings = len(buildings)
        building_names = list(buildings.keys())

        # Verificación 1: Debe haber EXACTLY 1 edificio
        if num_buildings != 1:
            self.errors.append(f"CRÍTICO: {num_buildings} edificios encontrados. Debe ser 1.")
            print(f"  ❌ FOUND {num_buildings} buildings (MUST be 1)")
            return
        else:
            print(f"  ✓ Exactly 1 building found")

        # Verificación 2: El edificio DEBE ser "Mall_Iquitos"
        if building_names[0] != "Mall_Iquitos":
            self.errors.append(f"CRÍTICO: Edificio '{building_names[0]}' no es 'Mall_Iquitos'")
            print(f"  ❌ Building name '{building_names[0]}' is NOT 'Mall_Iquitos'")
            return
        else:
            print(f"  ✓ Building name is 'Mall_Iquitos'")

        # Verificación 3: Contar cargadores en schema
        mall = buildings["Mall_Iquitos"]
        chargers = mall.get("chargers", {})
        num_chargers = len(chargers)

        if num_chargers != 128:
            self.warnings.append(f"Advertencia: {num_chargers} cargadores encontrados (esperado 128)")
            print(f"  ⚠️  Found {num_chargers} chargers (expected 128)")
        else:
            print(f"  ✓ 128 chargers configured")

        # Verificación 4: Verificar que los cargadores referencian charger_simulation_*.csv
        charger_refs = []
        for name, config in chargers.items():
            sim_file = config.get("charger_simulation")
            if not sim_file:
                self.errors.append(f"ERROR: Cargador '{name}' sin charger_simulation referencia")
            elif not sim_file.startswith("charger_simulation_"):
                self.errors.append(f"ERROR: Cargador '{name}' usa archivo '{sim_file}' (debe ser charger_simulation_*.csv)")
            else:
                charger_refs.append(sim_file)

        if not self.errors:
            print(f"  ✓ All {num_chargers} chargers reference charger_simulation_*.csv")

        print()

    def _check_no_building_csv(self):
        """Verificar que NO existan Building_*.csv."""
        print("[PASO 2] Verificar NO existan Building_*.csv")
        print("-" * 80)

        building_files = list(self.citylearn_dir.glob("Building_*.csv"))

        if building_files:
            self.errors.append(f"CRÍTICO: {len(building_files)} Building_*.csv archivos encontrados")
            for f in building_files[:5]:
                print(f"  ❌ {f.name} (debe ser eliminado)")
            if len(building_files) > 5:
                print(f"  ❌ ... y {len(building_files)-5} archivos más")
        else:
            print(f"  ✓ NO Building_*.csv files found")

        print()

    def _check_no_charger_old_format(self):
        """Verificar que NO existan charger_X_Y.csv (formato antiguo)."""
        print("[PASO 3] Verificar NO existan charger_*_*.csv (formato antiguo)")
        print("-" * 80)

        old_chargers = [f for f in self.citylearn_dir.glob("charger_*.csv")
                       if "_" in f.stem and not f.stem.startswith("charger_simulation")]

        if old_chargers:
            self.errors.append(f"CRÍTICO: {len(old_chargers)} charger_*_*.csv archivos (formato antiguo) encontrados")
            for f in old_chargers[:5]:
                print(f"  ❌ {f.name} (debe ser eliminado)")
            if len(old_chargers) > 5:
                print(f"  ❌ ... y {len(old_chargers)-5} archivos más")
        else:
            print(f"  ✓ NO old-format charger_*_*.csv files found")

        print()

    def _check_no_washing_machines(self):
        """Verificar que NO existan Washing_Machine_*.csv."""
        print("[PASO 4] Verificar NO existan Washing_Machine_*.csv")
        print("-" * 80)

        washing_files = list(self.citylearn_dir.glob("Washing_Machine_*.csv"))

        if washing_files:
            self.errors.append(f"CRÍTICO: {len(washing_files)} Washing_Machine_*.csv encontrados")
            for f in washing_files:
                print(f"  ❌ {f.name} (debe ser eliminado)")
        else:
            print(f"  ✓ NO Washing_Machine_*.csv files found")

        print()

    def _check_no_alternate_schemas(self):
        """Verificar que NO existan schemas alternativos."""
        print("[PASO 5] Verificar NO existan schema_grid_only.json o schema_pv_bess.json")
        print("-" * 80)

        alt_schemas = [
            self.citylearn_dir / "schema_grid_only.json",
            self.citylearn_dir / "schema_pv_bess.json"
        ]

        found_alts = [f for f in alt_schemas if f.exists()]

        if found_alts:
            self.errors.append(f"CRÍTICO: {len(found_alts)} schemas alternativos encontrados")
            for f in found_alts:
                print(f"  ❌ {f.name} (debe ser eliminado)")
        else:
            print(f"  ✓ NO alternate schemas found")

        print()

    def _check_charger_simulation_files(self):
        """Verificar que existan TODOS los charger_simulation_*.csv (128 archivos)."""
        print("[PASO 6] Verificar charger_simulation_*.csv (debe haber 128)")
        print("-" * 80)

        charger_sims = sorted([f for f in self.citylearn_dir.glob("charger_simulation_*.csv")])
        num_chargers = len(charger_sims)

        if num_chargers != 128:
            self.errors.append(f"ERROR: {num_chargers} archivos charger_simulation_*.csv encontrados (debe ser 128)")
            print(f"  ❌ Found {num_chargers} files (expected 128)")
        else:
            print(f"  ✓ All 128 charger_simulation_*.csv files present")
            # Mostrar primeros y últimos para confirmación
            print(f"     First: {charger_sims[0].name}")
            print(f"     Last:  {charger_sims[-1].name}")

        print()

    def _check_directory_file_count(self):
        """Verificar estructura final del directorio."""
        print("[PASO 7] Resumen de archivos en directorio")
        print("-" * 80)

        all_files = list(self.citylearn_dir.glob("*"))
        csv_files = [f for f in all_files if f.suffix == ".csv"]
        json_files = [f for f in all_files if f.suffix == ".json"]

        print(f"  CSV files:  {len(csv_files)}")
        print(f"  JSON files: {len(json_files)}")
        print(f"  Total:      {len(all_files)}")

        # Esperado: 128 charger_simulation + 4 utility (weather, carbon, pricing, electrical_storage) = 132 CSV
        #           1 schema.json = 1 JSON
        #           Total = 133
        expected_csv = 132
        expected_json = 1
        expected_total = 133

        if len(csv_files) != expected_csv:
            self.warnings.append(f"CSV count: {len(csv_files)} (expected {expected_csv})")
        else:
            print(f"  ✓ CSV count correct ({expected_csv})")

        if len(json_files) != expected_json:
            self.errors.append(f"JSON count: {len(json_files)} (expected {expected_json})")
        else:
            print(f"  ✓ JSON count correct ({expected_json})")

        print()

    def _summary(self):
        """Imprimir resumen final."""
        print("=" * 80)
        print("RESUMEN DE VALIDACIÓN")
        print("=" * 80 + "\n")

        if self.errors:
            print(f"❌ ERRORES ENCONTRADOS: {len(self.errors)}\n")
            for i, err in enumerate(self.errors, 1):
                print(f"  {i}. {err}")
            print()

        if self.warnings:
            print(f"⚠️  ADVERTENCIAS: {len(self.warnings)}\n")
            for i, warn in enumerate(self.warnings, 1):
                print(f"  {i}. {warn}")
            print()

        if self.info:
            print(f"ℹ️  INFO: {len(self.info)}\n")
            for i, inf in enumerate(self.info, 1):
                print(f"  {i}. {inf}")
            print()

        # Checklist
        print("-" * 80)
        print("CHECKLIST POST-LIMPIEZA:\n")

        checks = [
            ("1 building (Mall_Iquitos)", len(self.errors) == 0),
            ("128 chargers", "charger_simulation" in str(self.errors)),
            ("NO Building_*.csv", len([e for e in self.errors if "Building_" in e]) == 0),
            ("NO charger_*_*.csv", len([e for e in self.errors if "charger_" in e and "_" in e]) == 0),
            ("NO Washing_Machine_*.csv", len([e for e in self.errors if "Washing" in e]) == 0),
            ("SOLO schema.json", len([e for e in self.errors if "JSON" in e]) == 0),
            ("128 charger_simulation_*.csv", len(self.errors) == 0),
        ]

        all_pass = len(self.errors) == 0

        for desc, passed in checks:
            status = "✓" if passed else "❌"
            print(f"  {status} {desc}")

        print("\n" + "=" * 80)

        if all_pass:
            print("✅ VALIDACIÓN EXITOSA")
            print("   Solo Mall_Iquitos está definido correctamente")
            print("   Sistema listo para ENTRENAMIENTO")
            return 0
        else:
            print("❌ VALIDACIÓN FALLIDA")
            print(f"   {len(self.errors)} error(es) encontrado(s)")
            print("   Corregir antes de entrenar")
            return 1


if __name__ == "__main__":
    validator = SingleBuildingValidator()
    code = validator.run_all_checks()
    sys.exit(code)
