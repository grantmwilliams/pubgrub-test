#!/usr/bin/env -S uv run --script

import json
import subprocess
import sys
import time
from pathlib import Path

def run_python_implementation(scenario_file):
    """Run the Python implementation on a scenario"""
    script_path = Path(__file__).parent / "run_python.py"
    try:
        result = subprocess.run(
            [str(script_path), scenario_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {
                "scenario": "unknown",
                "success": False,
                "error": f"Process failed with return code {result.returncode}: {result.stderr}",
                "runtime_ms": 0
            }
    except subprocess.TimeoutExpired:
        return {
            "scenario": "unknown", 
            "success": False,
            "error": "Timeout after 30 seconds",
            "runtime_ms": 30000
        }
    except Exception as e:
        return {
            "scenario": "unknown",
            "success": False,
            "error": f"Exception: {str(e)}",
            "runtime_ms": 0
        }

def run_rust_implementation(scenario_file):
    """Run the Rust implementation on a scenario"""
    script_path = Path(__file__).parent / "run_rust.sh"
    try:
        result = subprocess.run(
            [str(script_path), scenario_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {
                "scenario": "unknown",
                "success": False,
                "error": f"Process failed with return code {result.returncode}: {result.stderr}",
                "runtime_ms": 0
            }
    except subprocess.TimeoutExpired:
        return {
            "scenario": "unknown",
            "success": False, 
            "error": "Timeout after 30 seconds",
            "runtime_ms": 30000
        }
    except Exception as e:
        return {
            "scenario": "unknown",
            "success": False,
            "error": f"Exception: {str(e)}",
            "runtime_ms": 0
        }

def compare_results(python_result, rust_result):
    """Compare results from both implementations"""
    comparison = {
        "scenario": python_result.get("scenario", rust_result.get("scenario", "unknown")),
        "description": python_result.get("description", rust_result.get("description", "")),
        "python": python_result,
        "rust": rust_result,
        "agreement": {
            "success_match": python_result.get("success") == rust_result.get("success"),
            "solution_match": python_result.get("solution") == rust_result.get("solution"),
            "both_succeeded": python_result.get("success") and rust_result.get("success"),
            "both_failed": not python_result.get("success") and not rust_result.get("success")
        },
        "performance": {
            "python_runtime_ms": python_result.get("runtime_ms", 0),
            "rust_runtime_ms": rust_result.get("runtime_ms", 0),
            "speedup_factor": 0
        }
    }
    
    # Calculate speedup factor
    python_time = python_result.get("runtime_ms", 0)
    rust_time = rust_result.get("runtime_ms", 0)
    
    if rust_time > 0:
        comparison["performance"]["speedup_factor"] = python_time / rust_time
    
    return comparison

def main():
    if len(sys.argv) < 2:
        print("Usage: python compare_implementations.py <scenario_file> [scenario_file2] ...")
        sys.exit(1)
    
    scenario_files = sys.argv[1:]
    results = []
    
    for scenario_file in scenario_files:
        if not Path(scenario_file).exists():
            print(f"Error: Scenario file '{scenario_file}' not found", file=sys.stderr)
            continue
        
        print(f"Running scenario: {scenario_file}", file=sys.stderr)
        
        # Run both implementations
        python_result = run_python_implementation(scenario_file)
        rust_result = run_rust_implementation(scenario_file)
        
        # Compare results
        comparison = compare_results(python_result, rust_result)
        results.append(comparison)
        
        # Print brief status
        status = "✓" if comparison["agreement"]["success_match"] else "✗"
        print(f"  {status} Agreement: {comparison['agreement']['success_match']}, "
              f"Python: {python_result.get('runtime_ms', 0):.1f}ms, "
              f"Rust: {rust_result.get('runtime_ms', 0):.1f}ms", file=sys.stderr)
    
    # Output complete results as JSON
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()