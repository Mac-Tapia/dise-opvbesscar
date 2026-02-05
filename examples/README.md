# Examples Directory

This directory contains example scripts demonstrating various features of the pvbesscar project.

## Available Examples

### `tracing_example.py`
Demonstrates the tracing and performance monitoring infrastructure.

**Features shown:**
- Function-level tracing with `@trace_function`
- Performance tracking with `@trace_performance`
- Context manager tracing with `trace_operation()`
- Training-specific tracing with `TrainingTracer`
- Nested tracing for complex workflows

**Usage:**
```bash
python examples/tracing_example.py
```

**Output:**
- Console: Formatted traces with timing and performance metrics
- File: `logs/examples/tracing_example.log`

## Adding New Examples

When adding new example scripts:

1. Use clear, descriptive names
2. Include docstrings explaining what the example demonstrates
3. Make examples runnable standalone
4. Add usage instructions to this README
5. Keep examples focused on one concept

## See Also

- **Tracing Guide:** `docs/TRACING_GUIDE.md` - Full tracing documentation
- **Quick Reference:** `TRACING_QUICK_REF.md` - Quick reference card
