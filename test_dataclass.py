from dataclasses import dataclass

@dataclass
class TestConfig:
    value: str = "default"

cfg = TestConfig(value="custom")
print(f"bool(cfg) = {bool(cfg)}")
print(f"cfg is truthy: {bool(cfg)}")
