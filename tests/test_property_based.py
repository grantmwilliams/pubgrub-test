"""
Property-based testing for PubGrub resolver using hypothesis.

This module contains tests that verify invariants and properties
that should hold for all valid inputs to the resolver.
"""

from hypothesis import given, strategies as st, assume, settings

from pubgrub_resolver.package import Package, Dependency
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.term import Term
from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.resolver import solve_dependencies


# Strategy for generating valid version strings
version_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Nd", "Pc"), whitelist_characters="."),
    min_size=1,
    max_size=10,
).filter(
    lambda x: len(x.split(".")) <= 3
    and all(part.isdigit() for part in x.split(".") if part)
)

# Strategy for generating package names
package_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="-_"
    ),
    min_size=1,
    max_size=20,
).filter(lambda x: x[0].isalpha() and x[-1].isalnum())


def valid_version_string(s):
    """Check if a string is a valid version."""
    try:
        Version(s)
        return True
    except (ValueError, TypeError):
        return False


@st.composite
def version_gen(draw):
    """Generate valid Version objects."""
    major = draw(st.integers(min_value=0, max_value=99))
    minor = draw(st.integers(min_value=0, max_value=99))
    patch = draw(st.integers(min_value=0, max_value=99))
    version_str = f"{major}.{minor}.{patch}"
    return Version(version_str)


@st.composite
def package_gen(draw):
    """Generate valid Package objects."""
    name = draw(package_name_strategy)
    return Package(name)


@st.composite
def version_range_gen(draw):
    """Generate valid VersionRange objects."""
    min_version = draw(version_gen())
    max_version = draw(version_gen())

    # Ensure min <= max
    if min_version > max_version:
        min_version, max_version = max_version, min_version

    min_inclusive = draw(st.booleans())
    max_inclusive = draw(st.booleans())

    return VersionRange(min_version, max_version, min_inclusive, max_inclusive)


@st.composite
def term_gen(draw):
    """Generate valid Term objects."""
    package = draw(package_gen())
    version_range = draw(version_range_gen())
    positive = draw(st.booleans())

    return Term(package, version_range, positive)


@st.composite
def dependency_gen(draw):
    """Generate valid Dependency objects."""
    package = draw(package_gen())
    version_range = draw(version_range_gen())

    return Dependency(package, version_range)


class TestVersionProperties:
    """Property-based tests for Version class."""

    @given(version_gen())
    def test_version_string_roundtrip(self, version):
        """Version string representation should be parseable back to same version."""
        version_str = str(version)
        parsed_version = Version(version_str)
        assert parsed_version == version

    @given(version_gen(), version_gen())
    def test_version_comparison_transitivity(self, v1, v2):
        """Version comparison should be transitive."""
        # We can't test full transitivity with just two versions,
        # but we can test basic properties
        if v1 == v2:
            assert not (v1 < v2)
            assert not (v1 > v2)
        elif v1 < v2:
            assert not (v1 > v2)
            assert not (v1 == v2)
        else:
            assert v1 > v2
            assert not (v1 < v2)
            assert not (v1 == v2)

    @given(version_gen())
    def test_version_self_equality(self, version):
        """Version should be equal to itself."""
        assert version == version
        assert not (version < version)
        assert not (version > version)


class TestVersionRangeProperties:
    """Property-based tests for VersionRange class."""

    @given(version_range_gen())
    def test_version_range_contains_boundary_versions(self, vrange):
        """Version range should correctly handle boundary versions."""
        # Skip empty ranges
        assume(not vrange.is_empty())

        if vrange.min_version is not None:
            if vrange.include_min:
                assert vrange.contains(vrange.min_version)
            else:
                assert not vrange.contains(vrange.min_version)

        if vrange.max_version is not None:
            if vrange.include_max:
                assert vrange.contains(vrange.max_version)
            else:
                assert not vrange.contains(vrange.max_version)

    @given(version_range_gen(), version_range_gen())
    def test_version_range_intersection_commutativity(self, vr1, vr2):
        """Version range intersection should be commutative."""
        intersection1 = vr1.intersect(vr2)
        intersection2 = vr2.intersect(vr1)

        if intersection1 is None and intersection2 is None:
            return  # Both None, which is fine

        if intersection1 is None or intersection2 is None:
            assert intersection1 is None and intersection2 is None
        else:
            assert intersection1 == intersection2

    @given(version_range_gen())
    def test_version_range_self_intersection(self, vrange):
        """Version range should intersect with itself."""
        # Skip empty ranges that can't intersect with themselves
        assume(not vrange.is_empty())

        intersection = vrange.intersect(vrange)
        assert intersection is not None
        assert intersection == vrange


class TestTermProperties:
    """Property-based tests for Term class."""

    @given(term_gen())
    def test_term_negation_double_negation(self, term):
        """Double negation should return to original term."""
        negated = term.negate()
        double_negated = negated.negate()

        assert double_negated.package == term.package
        assert double_negated.version_range == term.version_range
        assert double_negated.positive == term.positive

    @given(term_gen())
    def test_term_self_intersection(self, term):
        """Term should intersect with itself."""
        # Skip terms with empty version ranges that can't intersect with themselves
        assume(not term.version_range.is_empty())

        intersection = term.intersect(term)
        assert intersection is not None
        assert intersection.package == term.package
        # The intersection should be satisfiable
        assert not intersection.is_failure()

    @given(term_gen())
    def test_term_satisfies_self(self, term):
        """Term should satisfy itself."""
        # Skip terms with empty version ranges
        assume(not term.version_range.is_empty())

        # A term should satisfy itself
        assert term.satisfies(term)


class TestResolverProperties:
    """Property-based tests for the PubGrub resolver."""

    @given(st.integers(min_value=1, max_value=5))
    @settings(max_examples=10, deadline=5000)
    def test_resolver_simple_chain(self, chain_length):
        """Resolver should handle simple dependency chains."""
        provider = SimpleDependencyProvider()

        # Create a chain of dependencies: pkg0 -> pkg1 -> pkg2 -> ... -> pkgN
        packages = []
        for i in range(chain_length + 1):
            pkg = provider.add_package(f"pkg{i}", is_root=(i == 0))
            packages.append(pkg)
            provider.add_version(pkg, Version("1.0.0"))

        # Add dependencies: pkg_i depends on pkg_{i+1}
        for i in range(chain_length):
            provider.add_dependency(
                packages[i],
                Version("1.0.0"),
                Dependency(packages[i + 1], VersionRange(Version("1.0.0"), None)),
            )

        # Resolve and verify
        result = solve_dependencies(provider, packages[0], Version("1.0.0"))

        assert result.success is True
        assert result.solution is not None

        # Verify all packages are assigned
        solution_dict = {}
        for assignment in result.solution.get_all_assignments():
            solution_dict[assignment.package.name] = assignment.version

        for i in range(chain_length + 1):
            assert f"pkg{i}" in solution_dict
            assert solution_dict[f"pkg{i}"] == Version("1.0.0")

    @given(st.integers(min_value=2, max_value=4))
    @settings(max_examples=10, deadline=5000)
    def test_resolver_diamond_dependency(self, depth):
        """Resolver should handle diamond dependency patterns."""
        provider = SimpleDependencyProvider()

        # Create diamond: root -> {left, right} -> shared
        root = provider.add_package("root", is_root=True)
        left = provider.add_package("left")
        right = provider.add_package("right")
        shared = provider.add_package("shared")

        # Add versions
        for pkg in [root, left, right, shared]:
            provider.add_version(pkg, Version("1.0.0"))

        # Add dependencies
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(left, VersionRange(Version("1.0.0"), None)),
        )
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(right, VersionRange(Version("1.0.0"), None)),
        )
        provider.add_dependency(
            left,
            Version("1.0.0"),
            Dependency(shared, VersionRange(Version("1.0.0"), None)),
        )
        provider.add_dependency(
            right,
            Version("1.0.0"),
            Dependency(shared, VersionRange(Version("1.0.0"), None)),
        )

        # Resolve and verify
        result = solve_dependencies(provider, root, Version("1.0.0"))

        assert result.success is True
        assert result.solution is not None

        # Verify solution contains all packages
        solution_dict = {}
        for assignment in result.solution.get_all_assignments():
            solution_dict[assignment.package.name] = assignment.version

        expected_packages = {"root", "left", "right", "shared"}
        assert set(solution_dict.keys()) == expected_packages

        # Verify all versions are 1.0.0
        for version in solution_dict.values():
            assert version == Version("1.0.0")


class TestResolverInvariants:
    """Test invariants that should hold for all resolver operations."""

    def test_resolver_solution_satisfies_all_constraints(self):
        """Any successful resolution should satisfy all constraints."""
        # Create a simple scenario
        provider = SimpleDependencyProvider()
        root = provider.add_package("root", is_root=True)
        dep = provider.add_package("dep")

        provider.add_version(root, Version("1.0.0"))
        provider.add_version(dep, Version("1.0.0"))
        provider.add_version(dep, Version("2.0.0"))

        # Root depends on dep >= 1.0.0
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(dep, VersionRange(Version("1.0.0"), None)),
        )

        result = solve_dependencies(provider, root, Version("1.0.0"))

        assert result.success is True
        assert result.solution is not None

        # Verify the solution satisfies the constraint
        solution_dict = {}
        for assignment in result.solution.get_all_assignments():
            solution_dict[assignment.package.name] = assignment.version

        assert "root" in solution_dict
        assert "dep" in solution_dict
        assert solution_dict["dep"] >= Version("1.0.0")

    def test_resolver_failure_has_explanation(self):
        """Failed resolutions should provide meaningful error messages."""
        provider = SimpleDependencyProvider()
        root = provider.add_package("root", is_root=True)
        a = provider.add_package("a")
        b = provider.add_package("b")

        provider.add_version(root, Version("1.0.0"))
        provider.add_version(a, Version("1.0.0"))
        provider.add_version(b, Version("1.0.0"))

        # Create impossible constraints
        provider.add_dependency(
            root, Version("1.0.0"), Dependency(a, VersionRange(Version("1.0.0"), None))
        )
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(b, VersionRange(None, Version("1.0.0"), True, False)),
        )
        provider.add_dependency(
            a, Version("1.0.0"), Dependency(b, VersionRange(Version("1.0.0"), None))
        )

        result = solve_dependencies(provider, root, Version("1.0.0"))

        assert result.success is False
        assert result.solution is None
        assert result.error is not None
        assert len(result.error) > 0

    def test_resolver_deterministic_behavior(self):
        """Resolver should produce deterministic results for the same input."""
        provider = SimpleDependencyProvider()
        root = provider.add_package("root", is_root=True)
        dep = provider.add_package("dep")

        provider.add_version(root, Version("1.0.0"))
        provider.add_version(dep, Version("1.0.0"))
        provider.add_version(dep, Version("2.0.0"))

        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(dep, VersionRange(Version("1.0.0"), None)),
        )

        # Run resolution multiple times
        results = []
        for _ in range(3):
            result = solve_dependencies(provider, root, Version("1.0.0"))
            results.append(result)

        # All results should be identical
        for i in range(1, len(results)):
            assert results[i].success == results[0].success

            if results[0].success:
                # Compare solutions
                solution_0 = {
                    a.package.name: a.version
                    for a in results[0].solution.get_all_assignments()
                }
                solution_i = {
                    a.package.name: a.version
                    for a in results[i].solution.get_all_assignments()
                }
                assert solution_0 == solution_i
