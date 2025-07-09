"""
Command Line Interface for PubGrub resolver.

This CLI provides an interactive way to test the resolver with custom
dependency scenarios and analyze resolution performance.
"""

import json
import sys
import time
from typing import Optional, Any

import click

from .dependency_provider import SimpleDependencyProvider
from .package import Package, Dependency
from .version import Version, VersionRange
from .resolver import solve_dependencies, PubGrubResolver


class PubGrubCLI:
    """Command line interface for PubGrub resolver."""

    def __init__(self):
        self.provider = SimpleDependencyProvider()
        self.packages: dict[str, Package] = {}

    def add_package(self, name: str, versions: list[str]) -> None:
        """Add a package with specified versions."""
        if name in self.packages:
            print(f"Package '{name}' already exists")
            return

        package = self.provider.add_package(name, is_root=(name == "root"))
        self.packages[name] = package

        for version_str in versions:
            try:
                version = Version(version_str)
                self.provider.add_version(package, version)
                print(f"Added {name}@{version_str}")
            except ValueError as e:
                print(f"Error adding version {version_str} to {name}: {e}")

    def add_dependency(
        self,
        package_name: str,
        package_version: str,
        dep_name: str,
        dep_constraint: str,
    ) -> None:
        """Add a dependency between packages."""
        if package_name not in self.packages:
            print(f"Package '{package_name}' not found")
            return

        if dep_name not in self.packages:
            print(f"Dependency package '{dep_name}' not found")
            return

        try:
            package = self.packages[package_name]
            dep_package = self.packages[dep_name]
            package_ver = Version(package_version)

            # Parse dependency constraint
            dep_range = self._parse_version_constraint(dep_constraint)

            dependency = Dependency(dep_package, dep_range)
            self.provider.add_dependency(package, package_ver, dependency)

            print(
                f"Added dependency: {package_name}@{package_version} -> {dep_name} {dep_constraint}"
            )

        except ValueError as e:
            print(f"Error adding dependency: {e}")

    def _parse_version_constraint(self, constraint: str) -> VersionRange:
        """Parse a version constraint string into a VersionRange."""
        constraint = constraint.strip()

        # Handle special cases
        if constraint == "*" or constraint == "":
            return VersionRange(None, None)

        # Handle compound constraints like ">=1.0.0,<2.0.0"
        if "," in constraint:
            parts = [part.strip() for part in constraint.split(",")]
            min_version = None
            max_version = None
            min_inclusive = False
            max_inclusive = False

            for part in parts:
                if part.startswith(">="):
                    min_version = Version(part[2:].strip())
                    min_inclusive = True
                elif part.startswith(">"):
                    min_version = Version(part[1:].strip())
                    min_inclusive = False
                elif part.startswith("<="):
                    max_version = Version(part[2:].strip())
                    max_inclusive = True
                elif part.startswith("<"):
                    max_version = Version(part[1:].strip())
                    max_inclusive = False
                else:
                    raise ValueError(f"Unsupported constraint part: {part}")

            return VersionRange(min_version, max_version, min_inclusive, max_inclusive)

        # Handle exact version
        if not any(op in constraint for op in [">=", "<=", ">", "<", "~", "^"]):
            version = Version(constraint)
            return VersionRange(version, version, True, True)

        # Handle range operators
        if constraint.startswith(">="):
            version = Version(constraint[2:].strip())
            return VersionRange(version, None, True, False)
        elif constraint.startswith(">"):
            version = Version(constraint[1:].strip())
            return VersionRange(version, None, False, False)
        elif constraint.startswith("<="):
            version = Version(constraint[2:].strip())
            return VersionRange(None, version, False, True)
        elif constraint.startswith("<"):
            version = Version(constraint[1:].strip())
            return VersionRange(None, version, False, False)
        elif constraint.startswith("~"):
            # Tilde range: ~1.2.3 means >=1.2.3 and <1.3.0
            base_version = Version(constraint[1:].strip())
            parts = str(base_version).split(".")
            if len(parts) >= 2:
                next_minor = f"{parts[0]}.{int(parts[1]) + 1}.0"
                return VersionRange(base_version, Version(next_minor), True, False)
            else:
                return VersionRange(base_version, None, True, False)
        elif constraint.startswith("^"):
            # Caret range: ^1.2.3 means >=1.2.3 and <2.0.0
            base_version = Version(constraint[1:].strip())
            parts = str(base_version).split(".")
            if len(parts) >= 1:
                next_major = f"{int(parts[0]) + 1}.0.0"
                return VersionRange(base_version, Version(next_major), True, False)
            else:
                return VersionRange(base_version, None, True, False)

        # If we can't parse it, treat as exact version
        try:
            version = Version(constraint)
            return VersionRange(version, version, True, True)
        except ValueError:
            raise ValueError(f"Cannot parse version constraint: {constraint}")

    def resolve(
        self, root_package: str, root_version: str, verbose: bool = False
    ) -> None:
        """Resolve dependencies starting from root package."""
        if root_package not in self.packages:
            print(f"Root package '{root_package}' not found")
            return

        try:
            package = self.packages[root_package]
            version = Version(root_version)

            print(f"\nResolving dependencies for {root_package}@{root_version}...")
            start_time = time.perf_counter()

            result = solve_dependencies(self.provider, package, version)

            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000

            print(f"Resolution completed in {duration_ms:.2f}ms")

            if result.success:
                print("✅ Resolution successful!")
                print("\nSolution:")
                if result.solution is not None:
                    for assignment in result.solution.get_all_assignments():
                        print(f"  {assignment.package.name} = {assignment.version}")

                if verbose:
                    # Create a resolver to get statistics
                    resolver = PubGrubResolver(self.provider)
                    resolver.resolve(package, version)
                    stats = resolver.get_resolution_statistics()
                    print("\nStatistics:")
                    for key, value in stats.items():
                        print(f"  {key}: {value}")
            else:
                print("❌ Resolution failed!")
                print(f"Error: {result.error}")

        except ValueError as e:
            print(f"Error: {e}")

    def list_packages(self) -> None:
        """List all packages and their versions."""
        if not self.packages:
            print("No packages defined")
            return

        print("Packages:")
        for name, package in self.packages.items():
            versions = self.provider.get_package_versions(package)
            version_strs = [str(v) for v in sorted(versions)]
            print(f"  {name}: {', '.join(version_strs)}")

    def list_dependencies(self) -> None:
        """List all dependencies."""
        print("Dependencies:")
        deps_found = False
        for name, package in self.packages.items():
            versions = self.provider.get_package_versions(package)
            for version in versions:
                dependencies = self.provider.get_dependencies(package, version)
                if dependencies:
                    deps_found = True
                    print(f"  {name}@{version}:")
                    for dep in dependencies:
                        print(f"    -> {dep.package.name} {dep.version_range}")

        if not deps_found:
            print("  No dependencies defined")

    def load_scenario(self, filename: str) -> None:
        """Load a scenario from a JSON file."""
        try:
            with open(filename, "r") as f:
                data = json.load(f)

            # Clear existing state
            self.provider = SimpleDependencyProvider()
            self.packages = {}

            # Load packages
            for pkg_data in data.get("packages", []):
                name = pkg_data["name"]
                versions = pkg_data["versions"]
                self.add_package(name, versions)

            # Load dependencies
            for dep_data in data.get("dependencies", []):
                self.add_dependency(
                    dep_data["package"],
                    dep_data["version"],
                    dep_data["dependency"],
                    dep_data["constraint"],
                )

            print(f"Loaded scenario from {filename}")

        except FileNotFoundError:
            print(f"File {filename} not found")
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
        except KeyError as e:
            print(f"Missing required field in JSON: {e}")

    def save_scenario(self, filename: str) -> None:
        """Save current scenario to a JSON file."""
        data: dict[str, list[dict[str, Any]]] = {"packages": [], "dependencies": []}

        # Save packages
        for name, package in self.packages.items():
            versions = self.provider.get_package_versions(package)
            version_strs = [str(v) for v in sorted(versions)]
            data["packages"].append({"name": name, "versions": version_strs})

        # Save dependencies
        for name, package in self.packages.items():
            versions = self.provider.get_package_versions(package)
            for version in versions:
                dependencies = self.provider.get_dependencies(package, version)
                for dep in dependencies:
                    data["dependencies"].append(
                        {
                            "package": name,
                            "version": str(version),
                            "dependency": dep.package.name,
                            "constraint": str(dep.version_range),
                        }
                    )

        try:
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Scenario saved to {filename}")
        except IOError as e:
            print(f"Error saving file: {e}")

    def run_interactive(self) -> None:
        """Run interactive CLI mode."""
        print("PubGrub Resolver Interactive CLI")
        print("Type 'help' for available commands")

        while True:
            try:
                command = input("\npubgrub> ").strip().split()
                if not command:
                    continue

                cmd = command[0].lower()

                if cmd == "help":
                    self._print_help()
                elif cmd == "quit" or cmd == "exit":
                    print("Goodbye!")
                    break
                elif cmd == "add-package":
                    if len(command) < 3:
                        print("Usage: add-package <name> <version1> [version2] ...")
                        continue
                    name = command[1]
                    versions = command[2:]
                    self.add_package(name, versions)
                elif cmd == "add-dep":
                    if len(command) != 5:
                        print(
                            "Usage: add-dep <package> <version> <dependency> <constraint>"
                        )
                        continue
                    self.add_dependency(command[1], command[2], command[3], command[4])
                elif cmd == "resolve":
                    if len(command) < 3:
                        print("Usage: resolve <package> <version> [--verbose]")
                        continue
                    verbose = "--verbose" in command or "-v" in command
                    self.resolve(command[1], command[2], verbose)
                elif cmd == "list":
                    self.list_packages()
                elif cmd == "deps":
                    self.list_dependencies()
                elif cmd == "load":
                    if len(command) != 2:
                        print("Usage: load <filename>")
                        continue
                    self.load_scenario(command[1])
                elif cmd == "save":
                    if len(command) != 2:
                        print("Usage: save <filename>")
                        continue
                    self.save_scenario(command[1])
                elif cmd == "clear":
                    self.provider = SimpleDependencyProvider()
                    self.packages = {}
                    print("Cleared all packages and dependencies")
                else:
                    print(
                        f"Unknown command: {cmd}. Type 'help' for available commands."
                    )

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except EOFError:
                print("\nReceived EOF signal - exiting interactive mode.")
                print("This typically happens when input is redirected or piped.")
                break
            except Exception as e:
                print(f"Error: {e}")

    def _print_help(self) -> None:
        """Print help message."""
        help_text = """
Available commands:
  add-package <name> <version1> [version2] ...  Add a package with versions
  add-dep <pkg> <ver> <dep> <constraint>        Add a dependency
  resolve <package> <version> [--verbose]       Resolve dependencies
  list                                          List all packages
  deps                                          List all dependencies
  load <filename>                               Load scenario from JSON file
  save <filename>                               Save scenario to JSON file
  clear                                         Clear all packages and dependencies
  help                                          Show this help
  quit/exit                                     Exit the CLI

Version constraints:
  1.0.0       Exact version
  >=1.0.0     Greater than or equal
  >1.0.0      Greater than
  <=2.0.0     Less than or equal
  <2.0.0      Less than
  ~1.2.3      Tilde range (>=1.2.3, <1.3.0)
  ^1.2.3      Caret range (>=1.2.3, <2.0.0)
  *           Any version

Examples:
  add-package root 1.0.0
  add-package foo 1.0.0 1.1.0 2.0.0
  add-dep root 1.0.0 foo ">=1.0.0"
  resolve root 1.0.0
        """
        print(help_text)


def create_example_scenario(cli: PubGrubCLI) -> None:
    """Create an example scenario for demonstration."""
    print("Creating example scenario...")

    # Add packages
    cli.add_package("root", ["1.0.0"])
    cli.add_package("web-framework", ["1.0.0", "1.1.0", "2.0.0"])
    cli.add_package("database", ["1.0.0", "1.5.0", "2.0.0"])
    cli.add_package("logging", ["1.0.0", "1.2.0"])
    cli.add_package("crypto", ["1.0.0", "2.0.0"])

    # Add dependencies
    cli.add_dependency("root", "1.0.0", "web-framework", ">=1.0.0")
    cli.add_dependency("root", "1.0.0", "database", ">=1.0.0")
    cli.add_dependency("web-framework", "1.1.0", "logging", ">=1.0.0")
    cli.add_dependency("web-framework", "2.0.0", "crypto", ">=2.0.0")
    cli.add_dependency("database", "2.0.0", "crypto", ">=1.0.0")

    print("Example scenario created!")
    print("Try: resolve root 1.0.0")


@click.command()
@click.option("--scenario", help="Load scenario from JSON file")
@click.option(
    "--example", is_flag=True, help="Create example scenario and run non-interactively"
)
@click.option(
    "--resolve",
    nargs=2,
    metavar="PACKAGE VERSION",
    help="Resolve dependencies for package@version",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def main(
    scenario: Optional[str],
    example: bool,
    resolve: Optional[tuple[str, str]],
    verbose: bool,
):
    """PubGrub Resolver CLI - A dependency resolution tool."""
    cli = PubGrubCLI()

    # Load scenario if specified
    if scenario:
        cli.load_scenario(scenario)
    elif example:
        create_example_scenario(cli)
        # For example mode, run a sample resolution instead of interactive mode
        print("Running example resolution...")
        cli.resolve("root", "1.0.0", verbose)
        return

    # Resolve if specified
    if resolve:
        package, version = resolve
        cli.resolve(package, version, verbose)
    else:
        # Check if we're in a TTY before running interactive mode
        if not sys.stdin.isatty():
            click.echo(
                "Error: Interactive mode requires a TTY. Use --example or --resolve for non-interactive usage."
            )
            sys.exit(1)
        # Run interactive mode
        cli.run_interactive()


if __name__ == "__main__":
    main()
