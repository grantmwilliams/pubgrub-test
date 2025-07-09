#!/usr/bin/env python3

from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.package import Dependency
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.resolver import PubGrubResolver


def create_provider_scenario_2():
    """Avoiding conflict during decision making."""
    provider = SimpleDependencyProvider()

    # Add packages
    root = provider.add_package("root", is_root=True)
    foo = provider.add_package("foo")
    bar = provider.add_package("bar")

    # Add versions
    provider.add_version(root, Version("1.0.0"))
    provider.add_version(foo, Version("1.0.0"))
    provider.add_version(foo, Version("1.1.0"))
    provider.add_version(bar, Version("1.0.0"))
    provider.add_version(bar, Version("1.1.0"))
    provider.add_version(bar, Version("2.0.0"))

    # Dependencies
    # root 1.0.0 depends on foo [1.0.0, 2.0.0) and bar [1.0.0, 2.0.0)
    provider.add_dependency(
        root,
        Version("1.0.0"),
        Dependency(foo, VersionRange(Version("1.0.0"), Version("2.0.0"))),
    )
    provider.add_dependency(
        root,
        Version("1.0.0"),
        Dependency(bar, VersionRange(Version("1.0.0"), Version("2.0.0"))),
    )

    # foo 1.1.0 depends on bar [2.0.0, 3.0.0)
    provider.add_dependency(
        foo,
        Version("1.1.0"),
        Dependency(bar, VersionRange(Version("2.0.0"), Version("3.0.0"))),
    )

    return provider


def debug_scenario_2():
    provider = create_provider_scenario_2()
    root_package = provider.get_package_by_name("root")

    print("=== DEBUGGING SCENARIO 2 ===")

    resolver = PubGrubResolver(provider)
    resolver.root_package = root_package
    resolver.solution = resolver.solution.__class__()
    resolver.incompatibilities = resolver.incompatibilities.__class__()

    # Step 1: Add root constraint
    print("Step 1: Adding root constraint...")
    resolver._add_root_constraint(root_package, Version("1.0.0"))

    print(f"Solution: {resolver.solution}")
    print(f"Incompatibilities: {len(resolver.incompatibilities)}")
    for i, incomp in enumerate(resolver.incompatibilities.get_all()):
        print(f"  {i}: {incomp}")

    # Step 2: Unit propagation
    print("\nStep 2: Unit propagation...")
    unit_clauses = resolver.incompatibilities.find_unit_clauses(resolver.solution)
    print(f"Unit clauses: {len(unit_clauses)}")
    for clause in unit_clauses:
        print(f"  - {clause}")

    # Step 3: Check if we need to make a decision
    print("\nStep 3: Checking completion...")
    is_complete = resolver._is_complete_solution()
    print(f"Is complete: {is_complete}")

    if not is_complete:
        print("\nStep 4: Making decision...")
        unassigned = resolver._find_unassigned_packages()
        print(f"Unassigned packages: {[p.name for p in unassigned]}")

        if unassigned:
            package = unassigned[0]
            print(f"Choosing package: {package.name}")

            # Check available versions
            available_versions = resolver.provider.get_package_versions(package)
            print(f"Available versions: {[str(v) for v in available_versions]}")

            # Check compatibility
            for version in available_versions:
                is_compatible = resolver._is_version_compatible(package, version)
                print(f"  {version}: compatible = {is_compatible}")

                if not is_compatible:
                    # Debug why it's not compatible
                    print(f"    Debugging {package.name}@{version}...")

                    # Check existing incompatibilities
                    for incomp in resolver.incompatibilities.get_for_package(package):
                        term = incomp.get_term_for_package(package)
                        if term:
                            print(f"    Existing constraint: {term}")
                            if term.positive and not term.version_range.contains(
                                version
                            ):
                                print("      -> Violates positive constraint")
                            elif not term.positive and term.version_range.contains(
                                version
                            ):
                                print("      -> Violates negative constraint")

                    # Check future conflicts
                    deps = resolver.provider.get_dependencies(package, version)
                    print(f"    Dependencies: {len(deps)}")
                    for dep in deps:
                        print(f"      {dep.package.name} {dep.version_range}")

                        # Check if this dependency would conflict
                        for incomp in resolver.incompatibilities.get_for_package(
                            dep.package
                        ):
                            dep_term = incomp.get_term_for_package(dep.package)
                            if dep_term:
                                print(
                                    f"        Existing constraint on {dep.package.name}: {dep_term}"
                                )
                                if dep_term.positive:
                                    intersection = dep.version_range.intersect(
                                        dep_term.version_range
                                    )
                                    print(f"        Intersection: {intersection}")
                                    if intersection is None or intersection.is_empty():
                                        print("        -> CONFLICT!")


if __name__ == "__main__":
    debug_scenario_2()
