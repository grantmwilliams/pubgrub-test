"""
Package class for representing software packages.
"""

from __future__ import annotations

from .version import Version, VersionRange


class Package:
    """Represents a software package with a name and optional root status."""

    def __init__(self, name: str, is_root: bool = False) -> None:
        self.name = name
        self.is_root = is_root

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Package('{self.name}', is_root={self.is_root})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Package):
            return NotImplemented
        return self.name == other.name and self.is_root == other.is_root

    def __hash__(self) -> int:
        return hash((self.name, self.is_root))


class PackageSpec:
    """Represents a package specification with version constraints."""

    def __init__(self, package: Package, version_range: VersionRange) -> None:
        self.package = package
        self.version_range = version_range

    def __str__(self) -> str:
        return f"{self.package.name} {self.version_range}"

    def __repr__(self) -> str:
        return f"PackageSpec({self.package!r}, {self.version_range!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PackageSpec):
            return NotImplemented
        return (
            self.package == other.package and self.version_range == other.version_range
        )

    def __hash__(self) -> int:
        return hash((self.package, self.version_range))


class PackageVersion:
    """Represents a specific version of a package."""

    def __init__(self, package: Package, version: Version) -> None:
        self.package = package
        self.version = version

    def __str__(self) -> str:
        return f"{self.package.name}@{self.version}"

    def __repr__(self) -> str:
        return f"PackageVersion({self.package!r}, {self.version!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PackageVersion):
            return NotImplemented
        return self.package == other.package and self.version == other.version

    def __hash__(self) -> int:
        return hash((self.package, self.version))


class Dependency:
    """Represents a dependency relationship between packages."""

    def __init__(self, package: Package, version_range: VersionRange) -> None:
        self.package = package
        self.version_range = version_range

    def __str__(self) -> str:
        return f"{self.package.name} {self.version_range}"

    def __repr__(self) -> str:
        return f"Dependency({self.package!r}, {self.version_range!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Dependency):
            return NotImplemented
        return (
            self.package == other.package and self.version_range == other.version_range
        )

    def __hash__(self) -> int:
        return hash((self.package, self.version_range))
