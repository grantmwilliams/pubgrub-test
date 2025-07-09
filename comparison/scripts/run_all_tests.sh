#!/bin/bash

# Script to run all test scenarios and generate reports
# Usage: ./run_all_tests.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DATA_DIR="$SCRIPT_DIR/../test_data"
OUTPUTS_DIR="$SCRIPT_DIR/../outputs"
REPORTS_DIR="$SCRIPT_DIR/../reports"

# Create output directories
mkdir -p "$OUTPUTS_DIR" "$REPORTS_DIR"

echo "Running all test scenarios..."

# Find all test scenario files
SCENARIO_FILES=$(find "$TEST_DATA_DIR" -name "*.json" | sort)

if [ -z "$SCENARIO_FILES" ]; then
    echo "No test scenario files found in $TEST_DATA_DIR"
    exit 1
fi

# Run comparison on all scenarios
RESULTS_FILE="$OUTPUTS_DIR/comparison_results.json"
REPORT_PREFIX="$REPORTS_DIR/comparison_report"

echo "Running comparison script..."
"$SCRIPT_DIR/compare_implementations.py" $SCENARIO_FILES > "$RESULTS_FILE"

echo "Generating reports..."
"$SCRIPT_DIR/generate_report.py" "$RESULTS_FILE" "$REPORT_PREFIX"

echo ""
echo "=== Test Run Complete ==="
echo "Results saved to: $RESULTS_FILE"
echo "Reports generated:"
echo "  HTML: $REPORT_PREFIX.html"
echo "  CSV: $REPORT_PREFIX.csv"
echo ""

# Show brief summary
echo "=== Summary ==="
python3 -c "
import json
with open('$RESULTS_FILE', 'r') as f:
    results = json.load(f)
    
total = len(results)
agreements = sum(1 for r in results if r['agreement']['success_match'])
both_succeeded = sum(1 for r in results if r['agreement']['both_succeeded'])
both_failed = sum(1 for r in results if r['agreement']['both_failed'])

print(f'Total scenarios: {total}')
print(f'Agreement rate: {agreements}/{total} ({agreements/total*100:.1f}%)')
print(f'Both succeeded: {both_succeeded}')
print(f'Both failed: {both_failed}')

if results:
    python_time = sum(r['performance']['python_runtime_ms'] for r in results)
    rust_time = sum(r['performance']['rust_runtime_ms'] for r in results)
    speedup = python_time / rust_time if rust_time > 0 else 0
    print(f'Overall speedup: {speedup:.2f}x')
"