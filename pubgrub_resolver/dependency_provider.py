"""
DependencyProvider interface for fetching package metadata.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from .package import Package, Dependency
from .version import Version
from .term import Term


class DependencyProvider(ABC):
    """
    Abstract interface for providing package dependency information.

    This interface abstracts away the specifics of how package metadata
    is obtained (e.g., from a registry, file system, etc.).
    """

    @abstractmethod
    def get_package_versions(self, package: Package) -> list[Version]:
        """Get all available versions for a package."""
        pass

    @abstractmethod
    def get_dependencies(self, package: Package, version: Version) -> list[Dependency]:
        """Get the dependencies for a specific package version."""
        pass

    @abstractmethod
    def package_exists(self, package: Package) -> bool:
        """Check if a package exists."""
        pass

    def get_latest_version(self, package: Package) -> Version | None:
        """Get the latest version of a package."""
        versions = self.get_package_versions(package)
        return max(versions) if versions else None

    def get_compatible_versions(self, package: Package, term: Term) -> list[Version]:
        """Get versions of a package that are compatible with a term."""
        if term.package != package:
            raise ValueError("Term package must match the requested package")

        all_versions = self.get_package_versions(package)

        if term.positive:
            # Positive term: include versions that satisfy the range
            return [v for v in all_versions if term.version_range.contains(v)]
        else:
            # Negative term: exclude versions that satisfy the range
            return [v for v in all_versions if not term.version_range.contains(v)]


class SimpleDependencyProvider(DependencyProvider):
    """
    Simple in-memory dependency provider for testing.

    This provider stores package information in memory dictionaries.
    """

    def __init__(self) -> None:
        self.packages: dict[str, Package] = {}
        self.versions: dict[Package, list[Version]] = {}
        self.dependencies: dict[tuple[Package, Version], list[Dependency]] = {}

    def add_package(self, package_name: str, is_root: bool = False) -> Package:
        """Add a package to the provider."""
        package = Package(package_name, is_root)
        self.packages[package_name] = package
        if package not in self.versions:
            self.versions[package] = []
        return package

    def add_version(self, package: Package, version: Version) -> None:
        """Add a version to a package."""
        if package not in self.versions:
            self.versions[package] = []
        if version not in self.versions[package]:
            self.versions[package].append(version)
            self.versions[package].sort()

    def add_dependency(
        self, package: Package, version: Version, dependency: Dependency
    ) -> None:
        """Add a dependency for a specific package version."""
        key = (package, version)
        if key not in self.dependencies:
            self.dependencies[key] = []
        self.dependencies[key].append(dependency)

    def get_package_versions(self, package: Package) -> list[Version]:
        """Get all available versions for a package."""
        return self.versions.get(package, []).copy()

    def get_dependencies(self, package: Package, version: Version) -> list[Dependency]:
        """Get the dependencies for a specific package version."""
        key = (package, version)
        return self.dependencies.get(key, []).copy()

    def package_exists(self, package: Package) -> bool:
        """Check if a package exists."""
        return package in self.versions

    def get_package_by_name(self, name: str) -> Package | None:
        """Get a package by name."""
        return self.packages.get(name)

    def __str__(self) -> str:
        return f"SimpleDependencyProvider({len(self.packages)} packages)"

    def __repr__(self) -> str:
        return f"SimpleDependencyProvider(packages={list(self.packages.keys())})"


class CachingDependencyProvider(DependencyProvider):
    """
    Caching wrapper for dependency providers.

    This provider caches results from another provider to improve performance.
    """

    def __init__(self, inner: DependencyProvider) -> None:
        self.inner = inner
        self._version_cache: dict[Package, list[Version]] = {}
        self._dependency_cache: dict[tuple[Package, Version], list[Dependency]] = {}
        self._existence_cache: dict[Package, bool] = {}

    def get_package_versions(self, package: Package) -> list[Version]:
        """Get all available versions for a package (cached)."""
        if package not in self._version_cache:
            self._version_cache[package] = self.inner.get_package_versions(package)
        return self._version_cache[package].copy()

    def get_dependencies(self, package: Package, version: Version) -> list[Dependency]:
        """Get the dependencies for a specific package version (cached)."""
        key = (package, version)
        if key not in self._dependency_cache:
            self._dependency_cache[key] = self.inner.get_dependencies(package, version)
        return self._dependency_cache[key].copy()

    def package_exists(self, package: Package) -> bool:
        """Check if a package exists (cached)."""
        if package not in self._existence_cache:
            self._existence_cache[package] = self.inner.package_exists(package)
        return self._existence_cache[package]

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._version_cache.clear()
        self._dependency_cache.clear()
        self._existence_cache.clear()

    def __str__(self) -> str:
        return f"CachingDependencyProvider({self.inner})"

    def __repr__(self) -> str:
        return f"CachingDependencyProvider({self.inner!r})"


class RegistryDependencyProvider(DependencyProvider):
    """
    Dependency provider that fetches from a package registry.

    This is a placeholder for future implementation that would
    fetch package information from real registries like PyPI.
    """

    def __init__(self, registry_url: str) -> None:
        self.registry_url = registry_url
        # TODO: Implement actual registry fetching
        raise NotImplementedError("Registry dependency provider not yet implemented")

    def get_package_versions(self, package: Package) -> list[Version]:
        """Get all available versions for a package from registry."""
        # TODO: Implement registry API calls
        raise NotImplementedError("Registry dependency provider not yet implemented")

    def get_dependencies(self, package: Package, version: Version) -> list[Dependency]:
        """Get the dependencies for a specific package version from registry."""
        # TODO: Implement registry API calls
        raise NotImplementedError("Registry dependency provider not yet implemented")

    def package_exists(self, package: Package) -> bool:
        """Check if a package exists in the registry."""
        # TODO: Implement registry API calls
        raise NotImplementedError("Registry dependency provider not yet implemented")


def create_test_provider() -> SimpleDependencyProvider:
    """Create a test dependency provider with some sample packages."""
    from .version import Version, VersionRange

    provider = SimpleDependencyProvider()

    # Add root package
    root = provider.add_package("root", is_root=True)
    provider.add_version(root, Version("1.0.0"))

    # Add some test packages
    foo = provider.add_package("foo")
    provider.add_version(foo, Version("1.0.0"))
    provider.add_version(foo, Version("1.1.0"))
    provider.add_version(foo, Version("2.0.0"))

    bar = provider.add_package("bar")
    provider.add_version(bar, Version("1.0.0"))
    provider.add_version(bar, Version("1.5.0"))

    baz = provider.add_package("baz")
    provider.add_version(baz, Version("1.0.0"))

    # Add some dependencies
    # root 1.0.0 depends on foo >= 1.0.0
    root_dep = Dependency(foo, VersionRange(Version("1.0.0"), None))
    provider.add_dependency(root, Version("1.0.0"), root_dep)

    # foo 1.1.0 depends on bar >= 1.0.0
    foo_dep = Dependency(bar, VersionRange(Version("1.0.0"), None))
    provider.add_dependency(foo, Version("1.1.0"), foo_dep)

    # foo 2.0.0 depends on baz >= 1.0.0
    foo2_dep = Dependency(baz, VersionRange(Version("1.0.0"), None))
    provider.add_dependency(foo, Version("2.0.0"), foo2_dep)

    return provider
