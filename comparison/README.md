# PubGrub Implementation Comparison

This directory contains scripts and test data for comparing the Python and Rust implementations of the PubGrub algorithm.

## Directory Structure

```
comparison/
├── test_data/          # JSON test scenarios
├── scripts/            # Comparison and execution scripts
├── outputs/            # Raw comparison results (JSON)
├── reports/            # Generated HTML and CSV reports
└── README.md          # This file
```

## Test Data Format

Test scenarios are stored as JSON files in `test_data/` with the following structure:

```json
{
  "name": "scenario_name",
  "description": "Description of the test scenario",
  "packages": [
    {
      "name": "package_name",
      "versions": ["1.0.0", "1.1.0", "2.0.0"]
    }
  ],
  "dependencies": [
    {
      "package": "package_name",
      "version": "1.0.0",
      "dependency": "other_package",
      "constraint": ">=1.0.0"
    }
  ]
}
```

## Scripts

### Individual Test Runners

- `run_python.py` - Runs a single scenario with the Python implementation
- `run_rust.sh` - Runs a single scenario with the Rust implementation

Usage:
```bash
./scripts/run_python.py test_data/basic_scenario.json
./scripts/run_rust.sh test_data/basic_scenario.json
```

### Comparison and Reporting

- `compare_implementations.py` - Compares both implementations on given scenarios
- `generate_report.py` - Generates HTML and CSV reports from comparison results
- `run_all_tests.sh` - Runs all tests and generates reports

Usage:
```bash
# Compare specific scenarios
./scripts/compare_implementations.py test_data/basic_scenario.json test_data/conflict_scenario.json

# Generate reports from results
./scripts/generate_report.py outputs/comparison_results.json reports/my_report

# Run all tests and generate reports
./scripts/run_all_tests.sh
```

## Test Scenarios

The included test scenarios cover:

1. **basic_scenario.json** - Simple dependency resolution with basic constraints
2. **conflict_scenario.json** - Conflicting dependencies that should fail resolution
3. **performance_scenario.json** - Larger scenario for performance testing

## Output Format

The comparison scripts output structured JSON results containing:

- Success/failure status for each implementation
- Resolution solutions (if successful)
- Error messages (if failed)
- Runtime performance metrics
- Agreement analysis between implementations

## Reports

Generated reports include:

- **HTML Report** - Interactive web-based report with detailed comparisons
- **CSV Report** - Tabular data suitable for spreadsheet analysis

## Adding New Test Scenarios

To add a new test scenario:

1. Create a new JSON file in `test_data/` following the format above
2. Run `./scripts/run_all_tests.sh` to include it in the comparison

## Requirements

- Python implementation requires `uv` and the pubgrub_resolver package
- Rust implementation requires `cargo` and the rust_implementation submodule
- Both implementations should be properly set up and accessible from the comparison directory