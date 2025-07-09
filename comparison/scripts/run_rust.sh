#!/bin/bash

# Script to run Rust implementation with a test scenario
# Usage: ./run_rust.sh <scenario_file>

set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 <scenario_file>" >&2
    exit 1
fi

SCENARIO_FILE="$(realpath "$1")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUST_DIR="$SCRIPT_DIR/../../rust_implementation"

if [ ! -f "$SCENARIO_FILE" ]; then
    echo "Error: Scenario file '$SCENARIO_FILE' not found" >&2
    exit 1
fi

# Create a temporary Rust program to run the scenario
TEMP_DIR=$(mktemp -d)
TEMP_RUST_FILE="$TEMP_DIR/scenario_runner.rs"

cat > "$TEMP_RUST_FILE" << 'EOF'
use std::collections::HashMap;
use std::env;
use std::fs;
use std::time::Instant;
use serde::{Deserialize, Serialize};
use serde_json;

// Include the pubgrub library
use pubgrub::{resolve, OfflineDependencyProvider, Ranges};

#[derive(Debug, Deserialize)]
struct PackageData {
    name: String,
    versions: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct DependencyData {
    package: String,
    version: String,
    dependency: String,
    constraint: String,
}

#[derive(Debug, Deserialize)]
struct ScenarioData {
    name: String,
    description: Option<String>,
    packages: Vec<PackageData>,
    dependencies: Vec<DependencyData>,
}

#[derive(Debug, Serialize)]
struct RunResult {
    scenario: String,
    description: String,
    success: bool,
    solution: Option<HashMap<String, String>>,
    error: Option<String>,
    runtime_ms: f64,
}

// Simple version type for this example
type Version = u32;
type VersionSet = Ranges<Version>;

fn parse_version(version_str: &str) -> Result<Version, String> {
    // Convert semantic version to simple number (e.g., "1.0.0" -> 100, "1.1.0" -> 110)
    let parts: Vec<&str> = version_str.split('.').collect();
    if parts.len() != 3 {
        return Err(format!("Invalid version format: {}", version_str));
    }
    
    let major: u32 = parts[0].parse().map_err(|_| format!("Invalid major version: {}", parts[0]))?;
    let minor: u32 = parts[1].parse().map_err(|_| format!("Invalid minor version: {}", parts[1]))?;
    let patch: u32 = parts[2].parse().map_err(|_| format!("Invalid patch version: {}", parts[2]))?;
    
    Ok(major * 100 + minor * 10 + patch)
}

fn parse_constraint(constraint: &str) -> Result<VersionSet, String> {
    let constraint = constraint.trim();
    
    // Handle compound constraints like ">=1.0.0,<2.0.0"
    if constraint.contains(',') {
        let parts: Vec<&str> = constraint.split(',').map(|s| s.trim()).collect();
        let mut result = Ranges::full();
        
        for part in parts {
            let part_constraint = parse_single_constraint(part)?;
            result = result.intersection(&part_constraint);
        }
        
        Ok(result)
    } else {
        parse_single_constraint(constraint)
    }
}

fn parse_single_constraint(constraint: &str) -> Result<VersionSet, String> {
    let constraint = constraint.trim();
    if constraint.starts_with(">=") {
        let version_str = &constraint[2..].trim();
        let version = parse_version(version_str)?;
        Ok(Ranges::higher_than(version))
    } else if constraint.starts_with(">") {
        let version_str = &constraint[1..].trim();
        let version = parse_version(version_str)?;
        Ok(Ranges::strictly_higher_than(version))
    } else if constraint.starts_with("<=") {
        let version_str = &constraint[2..].trim();
        let version = parse_version(version_str)?;
        Ok(Ranges::lower_than(version))
    } else if constraint.starts_with("<") {
        let version_str = &constraint[1..].trim();
        let version = parse_version(version_str)?;
        Ok(Ranges::strictly_lower_than(version))
    } else if constraint == "*" {
        Ok(Ranges::full())
    } else {
        // Exact version
        let version = parse_version(constraint)?;
        Ok(Ranges::singleton(version))
    }
}

fn version_to_string(version: Version) -> String {
    let major = version / 100;
    let minor = (version % 100) / 10;
    let patch = version % 10;
    format!("{}.{}.{}", major, minor, patch)
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("Usage: {} <scenario_file>", args[0]);
        std::process::exit(1);
    }
    
    let scenario_file = &args[1];
    let scenario_content = fs::read_to_string(scenario_file)
        .expect("Failed to read scenario file");
    
    let scenario: ScenarioData = serde_json::from_str(&scenario_content)
        .expect("Failed to parse scenario JSON");
    
    let mut result = RunResult {
        scenario: scenario.name.clone(),
        description: scenario.description.clone().unwrap_or_default(),
        success: false,
        solution: None,
        error: None,
        runtime_ms: 0.0,
    };
    
    let start_time = Instant::now();
    
    // Create dependency provider
    let mut provider = OfflineDependencyProvider::<&str, VersionSet>::new();
    
    // Add all packages and their versions
    for pkg_data in &scenario.packages {
        for version_str in &pkg_data.versions {
            if let Ok(version) = parse_version(version_str) {
                provider.add_dependencies(pkg_data.name.as_str(), version, []);
            }
        }
    }
    
    // Group dependencies by package-version
    let mut package_dependencies: HashMap<(&str, Version), Vec<(&str, VersionSet)>> = HashMap::new();
    
    for dep_data in &scenario.dependencies {
        if let (Ok(pkg_version), Ok(constraint)) = (
            parse_version(&dep_data.version),
            parse_constraint(&dep_data.constraint)
        ) {
            let key = (dep_data.package.as_str(), pkg_version);
            package_dependencies.entry(key)
                .or_insert_with(Vec::new)
                .push((dep_data.dependency.as_str(), constraint));
        }
    }
    
    // Add dependencies to provider
    for ((package, version), dependencies) in package_dependencies {
        provider.add_dependencies(package, version, dependencies);
    }
    
    // Try to resolve
    match resolve(&provider, "root", parse_version("1.0.0").unwrap()) {
        Ok(solution) => {
            result.success = true;
            let mut solution_map = HashMap::new();
            for (pkg, version) in solution {
                solution_map.insert(pkg.to_string(), version_to_string(version));
            }
            result.solution = Some(solution_map);
        }
        Err(err) => {
            result.error = Some(format!("{:?}", err));
        }
    }
    
    let duration = start_time.elapsed();
    result.runtime_ms = duration.as_secs_f64() * 1000.0;
    
    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}
EOF

# Create Cargo.toml for the temporary project
cat > "$TEMP_DIR/Cargo.toml" << EOF
[package]
name = "scenario_runner"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "scenario_runner"
path = "scenario_runner.rs"

[dependencies]
pubgrub = { path = "$RUST_DIR" }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
EOF

# Build and run the Rust program
cd "$TEMP_DIR"
cargo run --quiet -- "$SCENARIO_FILE"

# Clean up
rm -rf "$TEMP_DIR"