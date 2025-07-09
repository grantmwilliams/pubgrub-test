#!/usr/bin/env python3

from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.package import Dependency
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.resolver import PubGrubResolver


def create_conflict_test_provider():
    """Create a test provider with conflicting dependencies."""
    provider = SimpleDependencyProvider()

    # Add packages
    root = provider.add_package("root", is_root=True)
    a = provider.add_package("a")
    b = provider.add_package("b")
    c = provider.add_package("c")

    # Add versions
    provider.add_version(root, Version("1.0.0"))
    provider.add_version(a, Version("1.0.0"))
    provider.add_version(a, Version("2.0.0"))
    provider.add_version(b, Version("1.0.0"))
    provider.add_version(b, Version("2.0.0"))
    provider.add_version(c, Version("1.0.0"))
    provider.add_version(c, Version("2.0.0"))

    # Create conflicting dependencies
    # root depends on a >= 1.0.0 and b >= 1.0.0
    provider.add_dependency(
        root, Version("1.0.0"), Dependency(a, VersionRange(Version("1.0.0"), None))
    )
    provider.add_dependency(
        root, Version("1.0.0"), Dependency(b, VersionRange(Version("1.0.0"), None))
    )

    # a 2.0.0 depends on c >= 2.0.0
    provider.add_dependency(
        a, Version("2.0.0"), Dependency(c, VersionRange(Version("2.0.0"), None))
    )

    # b 2.0.0 depends on c < 2.0.0 (conflict!)
    provider.add_dependency(
        b,
        Version("2.0.0"),
        Dependency(c, VersionRange(None, Version("2.0.0"), True, False)),
    )

    return provider


def test_conflict_resolution():
    """Test the conflict resolution system."""
    print("Testing conflict resolution with conflicting dependencies...")

    provider = create_conflict_test_provider()
    root_package = provider.get_package_by_name("root")

    resolver = PubGrubResolver(provider)
    result = resolver.resolve(root_package, Version("1.0.0"))

    print(f"Resolution result: {result.success}")
    if result.success:
        print("Solution:")
        for assignment in result.solution.get_all_assignments():
            print(f"  {assignment.package.name} = {assignment.version}")

        # Show resolution statistics
        stats = resolver.get_resolution_statistics()
        print(f"Resolution statistics: {stats}")
    else:
        print(f"Error: {result.error}")

        # Show conflict statistics
        stats = resolver.get_resolution_statistics()
        print(f"Conflict statistics: {stats}")


if __name__ == "__main__":
    test_conflict_resolution()
