"""Temporary fix script: add F0 TensorBoard records to PPO and A2C."""

old = (
    '            # F0: situaci\u00f3n actual sin proyecto\n'
    '            self.logger.record("co2/sinproyecto_kg", self._ep_co2_sinproyecto_kg)'
)
new = (
    '            # F0: situaci\u00f3n actual sin proyecto & comparaci\u00f3n vs F0 (OE3)\n'
    '            self.logger.record("co2/sinproyecto_kg", self._ep_co2_sinproyecto_kg)\n'
    '            self.logger.record("co2/f0_vs_ctrl_pct", f0_vs_ctrl_pct)\n'
    '            self.logger.record("co2/f0_vs_baseline_pct", f0_vs_baseline_pct)'
)

files = [
    "scripts/train/train_ppo_citylearn.py",
    "scripts/train/train_a2c_citylearn.py",
]
for fname in files:
    with open(fname, encoding="utf-8") as f:
        content = f.read()
    count = content.count(old)
    print(f"{fname}: found {count} match(es)")
    if count == 1:
        content = content.replace(old, new)
        with open(fname, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  -> Updated OK")
    else:
        print(f"  -> Skipped (count={count})")
