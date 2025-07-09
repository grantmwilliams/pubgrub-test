#!/usr/bin/env python3

from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.version import Version
from pubgrub_resolver.resolver import PubGrubResolver

# Create a very simple test case
provider = SimpleDependencyProvider()
root = provider.add_package("root", is_root=True)
provider.add_version(root, Version("1.0.0"))

print("Testing very simple case...")
print(f"Root package: {root}")

# Test resolution with debug output
resolver = PubGrubResolver(provider)

# Add debug to the original method
original_resolve = resolver.resolve


def debug_resolve(root_package, root_version):
    print(f"Starting resolution for {root_package}@{root_version}")

    try:
        resolver.root_package = root_package
        resolver.solution = resolver.solution.__class__()
        resolver.incompatibilities = resolver.incompatibilities.__class__()

        # Add root constraint
        print("Adding root constraint...")
        resolver._add_root_constraint(root_package, root_version)
        print(f"Solution after root: {resolver.solution}")
        print(f"Incompatibilities count: {len(resolver.incompatibilities)}")

        # Main resolution loop
        iteration = 0
        while True:
            iteration += 1
            print(f"\n=== Iteration {iteration} ===")

            if iteration > 10:  # Safety break
                print("Breaking due to iteration limit")
                break

            # Unit propagation
            print("Unit propagation...")
            unit_clauses = resolver.incompatibilities.find_unit_clauses(
                resolver.solution
            )
            print(f"Unit clauses found: {len(unit_clauses)}")
            for clause in unit_clauses:
                print(f"  - {clause}")

            if not unit_clauses:
                print("No unit clauses, checking completion...")
                if resolver._is_complete_solution():
                    print("Solution is complete!")
                    return resolver.solution
                else:
                    print("Solution not complete, making decision...")
                    # Make a decision
                    unassigned = resolver._find_unassigned_packages()
                    print(f"Unassigned packages: {unassigned}")
                    break

            # Apply unit clauses
            for clause in unit_clauses:
                print(f"Applying unit clause: {clause}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return None


# Run debug version
result = debug_resolve(root, Version("1.0.0"))
print(f"Final result: {result}")
