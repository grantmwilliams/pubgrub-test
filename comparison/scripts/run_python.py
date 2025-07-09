#!/usr/bin/env -S uv run --script

import json
import sys
import time
import traceback
from pathlib import Path

# Add the parent directory to the path so we can import pubgrub_resolver
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pubgrub_resolver.resolver import PubGrubResolver
from pubgrub_resolver.dependency_provider import DependencyProvider
from pubgrub_resolver.package import Package, Dependency
from pubgrub_resolver.version import Version, VersionRange, parse_version_constraint

class TestDependencyProvider(DependencyProvider):
    def __init__(self, scenario_data):
        self.packages = {}
        self.dependencies = {}
        
        # Parse packages
        for pkg_data in scenario_data["packages"]:
            pkg_name = pkg_data["name"]
            self.packages[pkg_name] = [Version(v) for v in pkg_data["versions"]]
        
        # Parse dependencies
        for dep_data in scenario_data["dependencies"]:
            pkg_name = dep_data["package"]
            pkg_version = Version(dep_data["version"])
            dep_name = dep_data["dependency"]
            constraint = dep_data["constraint"]
            
            key = (pkg_name, pkg_version)
            if key not in self.dependencies:
                self.dependencies[key] = []
            self.dependencies[key].append((dep_name, constraint))
    
    def get_dependencies(self, package, version):
        key = (package.name, version)
        if key in self.dependencies:
            deps = []
            for dep_name, constraint in self.dependencies[key]:
                dep_package = Package(dep_name)
                # Parse constraint string to VersionRange
                version_range = parse_version_constraint(constraint)
                deps.append(Dependency(dep_package, version_range))
            return deps
        return []
    
    def get_package_versions(self, package):
        return self.packages.get(package.name, [])
    
    def package_exists(self, package):
        return package.name in self.packages

def run_scenario(scenario_file):
    """Run a single scenario and return results"""
    with open(scenario_file, 'r') as f:
        scenario_data = json.load(f)
    
    provider = TestDependencyProvider(scenario_data)
    resolver = PubGrubResolver(provider)
    
    result = {
        "scenario": scenario_data["name"],
        "description": scenario_data.get("description", ""),
        "success": False,
        "solution": None,
        "error": None,
        "runtime_ms": 0
    }
    
    start_time = time.time()
    
    try:
        # Try to resolve dependencies for root package
        resolution_result = resolver.resolve(Package("root"), Version("1.0.0"))
        result["success"] = resolution_result.success
        if resolution_result.success and resolution_result.solution:
            result["solution"] = {pkg.name: str(assignment.version) for pkg, assignment in resolution_result.solution.assignments.items()}
        else:
            result["error"] = resolution_result.error
    except Exception as e:
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
    
    end_time = time.time()
    result["runtime_ms"] = (end_time - start_time) * 1000
    
    return result

def main():
    if len(sys.argv) != 2:
        print("Usage: python run_python.py <scenario_file>", file=sys.stderr)
        sys.exit(1)
    
    scenario_file = sys.argv[1]
    result = run_scenario(scenario_file)
    
    # Output JSON result
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()