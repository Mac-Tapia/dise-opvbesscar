"""
Test del módulo de despacho de prioridades.

Valida:
1. Cascada de prioridades P1→P2→P3→P4→P5
2. Límites respetados (EV, BESS, Mall)
3. Validación de planes
4. Recompensas consistentes
5. Escenarios operacionales realistas
"""

import json
import logging
from typing import List, Dict, Any

from src.iquitos_citylearn.oe3.dispatch_priorities import (
    EnergyDispatcher,
    DispatchState,
    DispatchPriorities,
    DispatchPlan,
    validate_dispatch_plan,
    compute_dispatch_reward_bonus,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DispatchTest:
    """Suite de tests para despacho de prioridades."""
    
    def __init__(self):
        self.dispatcher = EnergyDispatcher()
        self.results = {"passed": 0, "failed": 0, "tests": []}
    
    def run_all(self):
        """Ejecuta todos los tests."""
        logger.info("=" * 80)
        logger.info("INICIANDO TESTS DE DESPACHO DE PRIORIDADES")
        logger.info("=" * 80)
        
        self.test_priority_1_pv_to_ev()
        self.test_priority_2_pv_to_bess()
        self.test_priority_3_bess_to_ev()
        self.test_priority_4_bess_saturated()
        self.test_priority_5_grid_import()
        self.test_cascada_completa()
        self.test_validacion_limites()
        self.test_recompensas()
        self.test_escenario_pico_real()
        self.test_escenario_noche_real()
        
        self.print_summary()
    
    def _run_test(self, test_name: str, test_func, state: DispatchState) -> bool:
        """Helper para ejecutar un test."""
        try:
            plan = self.dispatcher.dispatch(state)
            is_valid, msg = validate_dispatch_plan(plan, state, self.dispatcher.priorities)
            
            result = test_func(plan, state, is_valid, msg)
            
            status = "✓ PASS" if result else "✗ FAIL"
            self.results["tests"].append({
                "name": test_name,
                "status": status,
                "passed": result
            })
            
            if result:
                self.results["passed"] += 1
                logger.info(f"{status}: {test_name}")
            else:
                self.results["failed"] += 1
                logger.error(f"{status}: {test_name}")
            
            return result
        
        except Exception as e:
            logger.error(f"✗ ERROR en {test_name}: {e}")
            self.results["failed"] += 1
            self.results["tests"].append({
                "name": test_name,
                "status": "✗ ERROR",
                "passed": False,
                "error": str(e)
            })
            return False
    
    # ========== TESTS DE PRIORIDADES INDIVIDUALES ==========
    
    def test_priority_1_pv_to_ev(self):
        """P1: FV → EV (máxima prioridad)"""
        
        # Caso 1: Hay sol y demanda EV
        state1 = DispatchState(
            hour=18,
            is_peak_hour=True,
            pv_power_kw=100.0,
            bess_soc_percent=60.0,
            bess_capacity_kwh=2000.0,
            bess_power_available_kw=1200.0,
            ev_demand_kw=120.0,
            mall_demand_kw=200.0,
        )
        
        def test1(plan, state, is_valid, msg):
            # Debe enviar algo a EV (hasta 100 kW disponible)
            return plan.pv_to_ev_kw == 100.0 and is_valid
        
        self._run_test("P1: FV directo a EVs cuando hay sol y demanda", test1, state1)
        
        # Caso 2: Sin sol
        state2 = DispatchState(
            hour=22,
            is_peak_hour=False,
            pv_power_kw=0.05,  # Noche
            bess_soc_percent=60.0,
            bess_capacity_kwh=2000.0,
            bess_power_available_kw=1200.0,
            ev_demand_kw=50.0,
            mall_demand_kw=100.0,
        )
        
        def test2(plan, state, is_valid, msg):
            # Sin sol: P1 no activa, pv_to_ev debe ser 0
            return plan.pv_to_ev_kw == 0.0 and is_valid
        
        self._run_test("P1: Inactiva de noche (sin sol)", test2, state2)
    
    def test_priority_2_pv_to_bess(self):
        """P2: FV excedente → BESS"""
        
        # Caso 1: Hay PV excedente y BESS no saturada
        state1 = DispatchState(
            hour=11,
            is_peak_hour=False,
            pv_power_kw=3000.0,  # Mucho sol (pico solar)
            bess_soc_percent=40.0,  # 40% = 800 kWh, espacio para 1200 kWh
            bess_capacity_kwh=2000.0,
            bess_power_available_kw=1200.0,
            ev_demand_kw=50.0,  # Baja demanda EV en valle
            mall_demand_kw=400.0,
        )
        
        def test1(plan, state, is_valid, msg):
            # P1 toma 50 kW, quedan 2950
            # P2 debe tomar hasta 1200 kW (límite BESS) o capacidad restante
            # Con SOC=40%, capacidad restante = 1200 kWh, luego P2 can take 1200 kW
            return (
                plan.pv_to_ev_kw == 50.0 and
                plan.pv_to_bess_kw == 1200.0 and
                plan.bess_charging and
                is_valid
            )
        
        self._run_test("P2: Cargar BESS con PV excedente", test1, state1)
        
        # Caso 2: BESS saturada
        state2 = DispatchState(
            hour=11,
            is_peak_hour=False,
            pv_power_kw=2000.0,
            bess_soc_percent=95.0,  # SATURADA
            bess_capacity_kwh=2000.0,
            bess_power_available_kw=1200.0,
            ev_demand_kw=30.0,
            mall_demand_kw=300.0,
        )
        
        def test2(plan, state, is_valid, msg):
            # BESS saturada: P2 no activa, pv_to_bess = 0
            return plan.pv_to_bess_kw == 0.0 and is_valid
        
        self._run_test("P2: Inactiva cuando BESS saturada (SOC > 95%)", test2, state2)
    
    def test_priority_3_bess_to_ev(self):
        """P3: BESS → EV (especialmente noche)"""
        
        # Caso 1: Noche, hay demanda EV, BESS disponible
        state1 = DispatchState(
            hour=22,
            is_peak_hour=False,
            pv_power_kw=0.05,  # Noche
            bess_soc_percent=75.0,  # 1500 kWh disponible
            bess_capacity_kwh=2000.0,
            bess_power_available_kw=1200.0,
            ev_demand_kw=100.0,
            mall_demand_kw=200.0,
        )
        
        def test1(plan, state, is_valid, msg):
            # Sin sol: P3 activa, entrega hasta 100 kW a EV
            return (
                plan.bess_to_ev_kw == 100.0 and
                plan.pv_to_ev_kw == 0.0 and
                plan.bess_discharging and
                is_valid
            )
        
        self._run_test("P3: BESS a EVs en noche", test1, state1)
        
        # Caso 2: BESS depleted
        state2 = DispatchState(
            hour=22,
            is_peak_hour=False,
            pv_power_kw=0.05,
            bess_soc_percent=15.0,  # DEPLETED (< 20%)
            bess_capacity_kwh=2000.0,
            bess_power_available_kw=1200.0,
            ev_demand_kw=80.0,
            mall_demand_kw=150.0,
        )
        
        def test2(plan, state, is_valid, msg):
            # BESS bajo mínimo: P3 no activa
            return plan.bess_to_ev_kw == 0.0 and is_valid
        
        self._run_test("P3: Inactiva cuando BESS depleted (SOC < 20%)", test2, state2)
    
    def test_priority_4_bess_saturated(self):
        """P4: BESS saturada → MALL"""
        
        # Caso: BESS saturada, PV excedente, demanda mall
        state = DispatchState(
            hour=12,
            is_peak_hour=False,
            pv_power_kw=2500.0,
            bess_soc_percent=96.0,  # SATURADA
            bess_capacity_kwh=2000.0,
            bess_power_available_kw=1200.0,
            ev_demand_kw=40.0,
            mall_demand_kw=400.0,
        )
        
        def test_fn(plan, state, is_valid, msg):
            # P1(40) + P2(0, BESS saturada) + P4(400 a mall)
            return (
                plan.pv_to_ev_kw == 40.0 and
                plan.pv_to_bess_kw == 0.0 and
                plan.pv_to_mall_kw == 400.0 and
                is_valid
            )
        
        self._run_test("P4: Cargar mall cuando BESS saturada y sobra FV", test_fn, state)
    
    def test_priority_5_grid_import(self):
        """P5: Grid Import (último recurso)"""
        
        # Caso: Demanda no cubierta por FV ni BESS
        state = DispatchState(
            hour=19,
            is_peak_hour=True,
            pv_power_kw=0.0,  # Anochecer
            bess_soc_percent=40.0,  # 800 kWh
            bess_capacity_kwh=2000.0,
            bess_power_available_kw=1200.0,
            ev_demand_kw=150.0,  # Máxima demanda
            mall_demand_kw=300.0,
        )
        
        def test_fn(plan, state, is_valid, msg):
            # BESS suministra 150 a EV, pero mall queda con déficit
            # P5 importa lo que falta
            return (
                plan.grid_import_kw > 0 and  # Hay importación
                plan.bess_to_ev_kw > 0 and   # BESS activa
                is_valid
            )
        
        self._run_test("P5: Importar grid cuando hay déficit", test_fn, state)
    
    # ========== TESTS INTEGRADOS ==========
    
    def test_cascada_completa(self):
        """Cascada completa P1→P2→P3→P4→P5"""
        
        # Escenario mixto: algo de sol, demanda EV alta, BESS medio
        state = DispatchState(
            hour=17,
            is_peak_hour=False,
            pv_power_kw=800.0,  # Atardecer, algo de sol
            bess_soc_percent=70.0,  # 1400 kWh
            bess_capacity_kwh=2000.0,
            bess_power_available_kw=1200.0,
            ev_demand_kw=150.0,  # Demanda pico pre-carga
            mall_demand_kw=250.0,
        )
        
        def test_fn(plan, state, is_valid, msg):
            # Cascada esperada:
            # P1: 150 a EV (máximo)
            # P2: 0 (PV agotado)
            # P3: no activa (hay sol aún)
            # P4: no aplica (BESS no saturada)
            # P5: importar para mall
            
            total_pv = plan.pv_to_ev_kw + plan.pv_to_bess_kw + plan.pv_to_mall_kw
            return (
                plan.pv_to_ev_kw == 150.0 and
                total_pv <= 800.0 and  # No excede PV disponible
                plan.grid_import_kw >= 0 and
                is_valid
            )
        
        self._run_test("Cascada P1→P5 completa en escenario mixto", test_fn, state)
    
    def test_validacion_limites(self):
        """Validar que no se violen límites de operación"""
        
        test_cases = [
            {
                "name": "EV limit 150 kW",
                "state": DispatchState(
                    hour=18, is_peak_hour=True, pv_power_kw=500,
                    bess_soc_percent=80, bess_capacity_kwh=2000,
                    bess_power_available_kw=1200,
                    ev_demand_kw=200,  # > 150 kW
                    mall_demand_kw=300
                ),
                "check": lambda p: p.pv_to_ev_kw <= 150.0
            },
            {
                "name": "BESS max power 1200 kW",
                "state": DispatchState(
                    hour=11, is_peak_hour=False, pv_power_kw=4000,
                    bess_soc_percent=50, bess_capacity_kwh=2000,
                    bess_power_available_kw=1200,
                    ev_demand_kw=50, mall_demand_kw=200
                ),
                "check": lambda p: p.pv_to_bess_kw <= 1200.0
            },
            {
                "name": "BESS SOC min 20%",
                "state": DispatchState(
                    hour=22, is_peak_hour=False, pv_power_kw=0.05,
                    bess_soc_percent=20, bess_capacity_kwh=2000,
                    bess_power_available_kw=1200,
                    ev_demand_kw=100, mall_demand_kw=200
                ),
                "check": lambda p: p.bess_to_ev_kw == 0  # No descargar bajo 20%
            },
        ]
        
        for tc in test_cases:
            def test_fn(plan, state, is_valid, msg):
                return tc["check"](plan) and is_valid
            
            self._run_test(f"Límite: {tc['name']}", test_fn, tc["state"])
    
    def test_recompensas(self):
        """Validar cálculo de recompensas por despacho"""
        
        # Caso: Despacho optimal (todo P1, nada P5)
        state = DispatchState(
            hour=18, is_peak_hour=True, pv_power_kw=150,
            bess_soc_percent=85, bess_capacity_kwh=2000,
            bess_power_available_kw=1200,
            ev_demand_kw=150, mall_demand_kw=300
        )
        
        plan = self.dispatcher.dispatch(state)
        rewards = compute_dispatch_reward_bonus(plan, state)
        
        def test_fn(plan, state, is_valid, msg):
            # Recompensa total debe ser positiva (bonus por usar FV)
            return (
                rewards.get("total_dispatch_reward", 0) >= 0 and
                is_valid
            )
        
        # Simular test (ya calculado arriba)
        self.results["tests"].append({
            "name": "Recompensas: Total no-negativo en despacho optimal",
            "status": "✓ PASS" if test_fn(plan, state, True, "") else "✗ FAIL",
            "passed": test_fn(plan, state, True, "")
        })
        
        if test_fn(plan, state, True, ""):
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
    
    # ========== TESTS DE ESCENARIOS REALISTAS ==========
    
    def test_escenario_pico_real(self):
        """Escenario realista: Bloque pico (18-21h)"""
        
        logger.info("\nEscenario: Bloque pico (18-21h)")
        logger.info("-" * 60)
        
        for hour in [18, 19, 20, 21]:
            # En pico: poco/nada de sol, máxima demanda EV
            pv = max(0, 500 - (hour - 18) * 100)  # Decayendo
            
            state = DispatchState(
                hour=hour,
                is_peak_hour=True,
                pv_power_kw=pv,
                bess_soc_percent=85 - (hour - 18) * 15,  # Descargando lentamente
                bess_capacity_kwh=2000.0,
                bess_power_available_kw=1200.0,
                ev_demand_kw=145.0,  # Pico de carga
                mall_demand_kw=350.0,
            )
            
            plan = self.dispatcher.dispatch(state)
            is_valid, msg = validate_dispatch_plan(plan, state, self.dispatcher.priorities)
            
            logger.info(
                f"H{hour}: PV={pv:.0f}kW SOC={state.bess_soc_percent:.0f}% "
                f"→ {plan.priority_sequence} [Valid={is_valid}]"
            )
    
    def test_escenario_noche_real(self):
        """Escenario realista: Noche (22-06h)"""
        
        logger.info("\nEscenario: Noche (22-06h)")
        logger.info("-" * 60)
        
        for hour in [22, 23, 0, 1, 5, 6]:
            # Noche: sin sol, demanda EV moderada
            
            state = DispatchState(
                hour=hour,
                is_peak_hour=False,
                pv_power_kw=0.0,
                bess_soc_percent=55 - (hour % 6) * 5,  # SOC decreciente
                bess_capacity_kwh=2000.0,
                bess_power_available_kw=1200.0,
                ev_demand_kw=50.0 + (hour % 6) * 10,  # Varía según hora
                mall_demand_kw=150.0,
            )
            
            plan = self.dispatcher.dispatch(state)
            is_valid, msg = validate_dispatch_plan(plan, state, self.dispatcher.priorities)
            
            logger.info(
                f"H{hour}: SOC={state.bess_soc_percent:.0f}% EV_dem={state.ev_demand_kw:.0f}kW "
                f"→ BESS→EV={plan.bess_to_ev_kw:.0f}kW GRID={plan.grid_import_kw:.0f}kW "
                f"[Valid={is_valid}]"
            )
    
    def print_summary(self):
        """Imprime resumen de resultados."""
        
        logger.info("\n" + "=" * 80)
        logger.info("RESUMEN DE TESTS")
        logger.info("=" * 80)
        
        logger.info(f"✓ Pasados: {self.results['passed']}")
        logger.info(f"✗ Fallidos: {self.results['failed']}")
        logger.info(f"Total: {self.results['passed'] + self.results['failed']}")
        
        if self.results['failed'] == 0:
            logger.info("\n🎉 TODOS LOS TESTS PASARON")
        else:
            logger.info("\n⚠️  ALGUNOS TESTS FALLARON:")
            for test in self.results['tests']:
                if "FAIL" in test['status'] or "ERROR" in test['status']:
                    logger.info(f"  - {test['name']}: {test['status']}")


def main():
    """Punto de entrada para tests."""
    tester = DispatchTest()
    tester.run_all()
    
    # Salida JSON para CI/CD
    with open("dispatch_test_results.json", "w") as f:
        json.dump(tester.results, f, indent=2)
    
    logger.info(f"\nResultados guardados en: dispatch_test_results.json")
    
    return 0 if tester.results['failed'] == 0 else 1


if __name__ == "__main__":
    exit(main())
