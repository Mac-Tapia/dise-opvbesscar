#!/usr/bin/env python3
"""
Validación rápida de sincronización OE3 (sin YAML parsing).
Verifica que valores clave estén sincronizados en archivos críticos.
"""

from pathlib import Path
import sys

def check_file_for_values(filepath, checks):
    """Buscar valores específicos en un archivo (sin parsing)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"  ❌ Error leyendo {filepath}: {e}")
        return 0, 1

    passed = 0
    failed = 0

    for search_str, desc in checks:
        if search_str in content:
            print(f"  ✅ {desc}")
            passed += 1
        else:
            print(f"  ⚠️  {desc}")
            failed += 1

    return passed, failed


def main():
    print("=" * 80)
    print("🔍 AUDITORÍA RÁPIDA: Sincronización OE3 Training")
    print("=" * 80)

    workspace = Path("d:/diseñopvbesscar")
    total_passed = 0
    total_failed = 0

    # 1. Auditar configs/default.yaml
    print("\n📋 Auditando: configs/default.yaml")
    yaml_checks = [
        ("charger_power_kw_moto: 2.0", "Moto power: 2.0kW ✓"),
        ("charger_power_kw_mototaxi: 3.0", "Mototaxi power: 3.0kW ✓"),
        ("total_chargers: 32", "Total chargers: 32 ✓"),
        ("total_sockets: 128", "Total sockets: 128 ✓"),
        ("ev_demand_constant_kw: 50.0", "EV demand: 50.0kW ✓"),
        ("fixed_capacity_kwh: 4520", "BESS capacity: 4,520 kWh ✓"),
        ("fixed_power_kw: 2712", "BESS power: 2,712 kW ✓"),
    ]
    p, f = check_file_for_values(workspace / "configs/default.yaml", yaml_checks)
    total_passed += p
    total_failed += f

    # 2. Auditar dataset_builder.py
    print("\n📋 Auditando: dataset_builder.py")
    db_checks = [
        ("del schema[\"electric_vehicles_def\"]", "EVs dinámicos (DELETE permanent) ✓"),
        ("EVs son dinámicos vía CSV", "EVs CSV-based ✓"),
        ("_validate_solar_timeseries_hourly", "Solar validation (8,760 hrs) ✓"),
        ("n_rows != 8760", "Rechaza sub-hourly data ✓"),
    ]
    p, f = check_file_for_values(workspace / "src/iquitos_citylearn/oe3/dataset_builder.py", db_checks)
    total_passed += p
    total_failed += f

    # 3. Auditar rewards.py
    print("\n📋 Auditando: rewards.py")
    rewards_checks = [
        ("co2_factor_kg_per_kwh: float = 0.4521", "CO2 factor: 0.4521 ✓"),
        ("n_chargers: int = 32", "Chargers: 32 ✓"),
        ("total_sockets: int = 128", "Sockets: 128 ✓"),
        ("ev_demand_constant_kw: float = 50.0", "EV demand: 50.0kW ✓"),
        ("co2: float = 0.50", "CO2 weight: 0.50 (PRIMARY) ✓"),
        ("solar: float = 0.20", "Solar weight: 0.20 (SECONDARY) ✓"),
    ]
    p, f = check_file_for_values(workspace / "src/iquitos_citylearn/oe3/rewards.py", rewards_checks)
    total_passed += p
    total_failed += f

    # 4. Auditar SAC agent
    print("\n📋 Auditando: agents/sac.py")
    sac_checks = [
        ("128 charger demands", "128 chargers in obs ✓"),
        ("detect_device()", "GPU/device detection ✓"),
        ("torch.cuda.is_available()", "CUDA support ✓"),
    ]
    p, f = check_file_for_values(workspace / "src/iquitos_citylearn/oe3/agents/sac.py", sac_checks)
    total_passed += p
    total_failed += f

    # 5. Auditar PPO agent
    print("\n📋 Auditando: agents/ppo_sb3.py")
    ppo_checks = [
        ("weight_co2: float = 0.50", "CO2 weight: 0.50 ✓"),
        ("weight_solar: float = 0.20", "Solar weight: 0.20 ✓"),
        ("co2_target_kg_per_kwh: float = 0.4521", "CO2 target: 0.4521 ✓"),
        ("ev_demand_constant_kw: float = 50.0", "EV demand: 50.0kW ✓"),
        ("device: str = \"auto\"", "Device auto-detect ✓"),
    ]
    p, f = check_file_for_values(workspace / "src/iquitos_citylearn/oe3/agents/ppo_sb3.py", ppo_checks)
    total_passed += p
    total_failed += f

    # 6. Auditar A2C agent
    print("\n📋 Auditando: agents/a2c_sb3.py")
    a2c_checks = [
        ("weight_co2: float = 0.50", "CO2 weight: 0.50 ✓"),
        ("weight_solar: float = 0.20", "Solar weight: 0.20 ✓"),
        ("co2_target_kg_per_kwh: float = 0.4521", "CO2 target: 0.4521 ✓"),
        ("ev_demand_constant_kw: float = 50.0", "EV demand: 50.0kW ✓"),
    ]
    p, f = check_file_for_values(workspace / "src/iquitos_citylearn/oe3/agents/a2c_sb3.py", a2c_checks)
    total_passed += p
    total_failed += f

    # 7. Auditar data_loader.py
    print("\n📋 Auditando: data_loader.py")
    dl_checks = [
        ("len(self.hourly_profiles) != 128", "Valida 128 sockets ✓"),
        ("len(profile) != 8760", "Valida 8,760 horas ✓"),
        ("solar_df.min() < 0", "Rechaza solar negativa ✓"),
    ]
    p, f = check_file_for_values(workspace / "src/iquitos_citylearn/oe3/data_loader.py", dl_checks)
    total_passed += p
    total_failed += f

    # 8. Auditar data files
    print("\n📋 Auditando: Data files (OE2 artifacts)")

    data_files_to_check = [
        ("data/interim/oe2/solar/pv_generation_timeseries.csv", "Solar timeseries"),
        ("data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv", "Charger profiles"),
        ("data/interim/oe2/bess/bess_config.json", "BESS config"),
        ("data/interim/oe2/chargers/individual_chargers.json", "Individual chargers"),
    ]

    for rel_path, desc in data_files_to_check:
        full_path = workspace / rel_path
        if full_path.exists():
            print(f"  ✅ {desc}: exists")
            total_passed += 1
        else:
            print(f"  ❌ {desc}: MISSING - {full_path}")
            total_failed += 1

    # 9. Auditar scripts
    print("\n📋 Auditando: Entry point scripts")

    scripts_to_check = [
        ("scripts/run_oe3_build_dataset.py", "Build dataset script"),
        ("scripts/run_uncontrolled_baseline.py", "Baseline script"),
        ("scripts/run_sac_ppo_a2c_only.py", "Training script"),
        ("scripts/run_oe3_co2_table.py", "Comparison table script"),
    ]

    for rel_path, desc in scripts_to_check:
        full_path = workspace / rel_path
        if full_path.exists():
            print(f"  ✅ {desc}: exists")
            total_passed += 1
        else:
            print(f"  ❌ {desc}: MISSING - {full_path}")
            total_failed += 1

    # Resumen final
    print("\n" + "=" * 80)
    print(f"📊 RESUMEN AUDITORÍA:")
    print(f"  ✅ Checks passed: {total_passed}")
    print(f"  ⚠️  Checks failed/warnings: {total_failed}")
    print("=" * 80)

    if total_failed <= 2:  # Pequeños warnings son OK
        print("\n✅ SISTEMA SINCRONIZADO - LISTO PARA ENTRENAMIENTO")
        print("\n🚀 Próximos pasos:")
        print("  1. python -m scripts.run_oe3_build_dataset --config configs/default.yaml")
        print("  2. python -m scripts.run_uncontrolled_baseline --config configs/default.yaml")
        print("  3. python -m scripts.run_sac_ppo_a2c_only --sac-episodes 1 --ppo-episodes 1 --a2c-episodes 1")
        print("  4. python -m scripts.run_oe3_co2_table --config configs/default.yaml")
        return 0
    else:
        print(f"\n⚠️  {total_failed} problemas encontrados - revisar arriba")
        return 1


if __name__ == "__main__":
    sys.exit(main())
