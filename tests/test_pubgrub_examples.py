"""
Test cases based on pubgrub-rs examples.rs to ensure compatibility.
"""

from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.package import Package, Dependency
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.resolver import solve_dependencies


def create_provider_scenario_1():
    """No conflict test - simple dependency chain."""
    provider = SimpleDependencyProvider()

    # Add packages
    root = provider.add_package("root", is_root=True)
    foo = provider.add_package("foo")
    bar = provider.add_package("bar")

    # Add versions
    provider.add_version(root, Version("1.0.0"))
    provider.add_version(foo, Version("1.0.0"))
    provider.add_version(foo, Version("2.0.0"))
    provider.add_version(bar, Version("1.0.0"))
    provider.add_version(bar, Version("2.0.0"))

    # Dependencies
    # root 1.0.0 depends on foo [1.0.0, 2.0.0)
    provider.add_dependency(
        root,
        Version("1.0.0"),
        Dependency(foo, VersionRange(Version("1.0.0"), Version("2.0.0"))),
    )

    # foo 1.0.0 depends on bar [1.0.0, 2.0.0)
    provider.add_dependency(
        foo,
        Version("1.0.0"),
        Dependency(bar, VersionRange(Version("1.0.0"), Version("2.0.0"))),
    )

    return provider


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


def create_provider_scenario_3():
    """Conflict resolution test."""
    provider = SimpleDependencyProvider()

    # Add packages
    root = provider.add_package("root", is_root=True)
    foo = provider.add_package("foo")
    bar = provider.add_package("bar")

    # Add versions
    provider.add_version(root, Version("1.0.0"))
    provider.add_version(foo, Version("1.0.0"))
    provider.add_version(foo, Version("2.0.0"))
    provider.add_version(bar, Version("1.0.0"))
    provider.add_version(bar, Version("2.0.0"))

    # Dependencies
    # root 1.0.0 depends on foo > 1.0.0
    provider.add_dependency(
        root,
        Version("1.0.0"),
        Dependency(foo, VersionRange(Version("1.0.0"), None, False, False)),
    )

    # foo 2.0.0 depends on bar [1.0.0, 2.0.0)
    provider.add_dependency(
        foo,
        Version("2.0.0"),
        Dependency(bar, VersionRange(Version("1.0.0"), Version("2.0.0"))),
    )

    return provider


def create_provider_partial_satisfier():
    """Complex scenario with partial satisfier."""
    provider = SimpleDependencyProvider()

    # Add packages
    root = provider.add_package("root", is_root=True)
    foo = provider.add_package("foo")
    bar = provider.add_package("bar")
    left = provider.add_package("left")
    right = provider.add_package("right")
    shared = provider.add_package("shared")
    target = provider.add_package("target")

    # Add versions
    provider.add_version(root, Version("1.0.0"))
    provider.add_version(foo, Version("1.0.0"))
    provider.add_version(bar, Version("1.0.0"))
    provider.add_version(left, Version("1.0.0"))
    provider.add_version(right, Version("1.0.0"))
    provider.add_version(shared, Version("1.0.0"))
    provider.add_version(shared, Version("2.0.0"))
    provider.add_version(target, Version("1.0.0"))
    provider.add_version(target, Version("2.0.0"))

    # Dependencies
    # root depends on foo and bar
    provider.add_dependency(
        root, Version("1.0.0"), Dependency(foo, VersionRange(Version("1.0.0"), None))
    )
    provider.add_dependency(
        root, Version("1.0.0"), Dependency(bar, VersionRange(Version("1.0.0"), None))
    )

    # foo depends on left and right
    provider.add_dependency(
        foo, Version("1.0.0"), Dependency(left, VersionRange(Version("1.0.0"), None))
    )
    provider.add_dependency(
        foo, Version("1.0.0"), Dependency(right, VersionRange(Version("1.0.0"), None))
    )

    # bar depends on shared and target
    provider.add_dependency(
        bar, Version("1.0.0"), Dependency(shared, VersionRange(Version("1.0.0"), None))
    )
    provider.add_dependency(
        bar, Version("1.0.0"), Dependency(target, VersionRange(Version("1.0.0"), None))
    )

    # left depends on shared >= 2.0.0
    provider.add_dependency(
        left, Version("1.0.0"), Dependency(shared, VersionRange(Version("2.0.0"), None))
    )

    # right depends on target >= 2.0.0
    provider.add_dependency(
        right,
        Version("1.0.0"),
        Dependency(target, VersionRange(Version("2.0.0"), None)),
    )

    return provider


def create_provider_double_choices():
    """Test double choices scenario."""
    provider = SimpleDependencyProvider()

    # Add packages
    root = provider.add_package("root", is_root=True)
    a = provider.add_package("a")
    b = provider.add_package("b")
    c = provider.add_package("c")
    d = provider.add_package("d")

    # Add versions
    provider.add_version(root, Version("1.0.0"))
    provider.add_version(a, Version("1.0.0"))
    provider.add_version(b, Version("1.0.0"))
    provider.add_version(c, Version("1.0.0"))
    provider.add_version(d, Version("1.0.0"))

    # Dependencies
    # root depends on a
    provider.add_dependency(
        root, Version("1.0.0"), Dependency(a, VersionRange(Version("1.0.0"), None))
    )

    # a depends on b
    provider.add_dependency(
        a, Version("1.0.0"), Dependency(b, VersionRange(Version("1.0.0"), None))
    )

    # b depends on c
    provider.add_dependency(
        b, Version("1.0.0"), Dependency(c, VersionRange(Version("1.0.0"), None))
    )

    # c depends on d
    provider.add_dependency(
        c, Version("1.0.0"), Dependency(d, VersionRange(Version("1.0.0"), None))
    )

    return provider


class TestPubGrubExamples:
    """Test cases matching pubgrub-rs examples."""

    def test_no_conflict(self):
        """Test no conflict scenario."""
        provider = create_provider_scenario_1()
        root_package = provider.get_package_by_name("root")

        result = solve_dependencies(provider, root_package, Version("1.0.0"))

        assert result.success is True
        assert result.solution is not None

        # Check expected solution
        solution_dict = {}
        for assignment in result.solution.get_all_assignments():
            solution_dict[assignment.package.name] = str(assignment.version)

        expected = {"root": "1.0.0", "foo": "1.0.0", "bar": "1.0.0"}

        assert solution_dict == expected

    def test_avoiding_conflict_during_decision_making(self):
        """Test avoiding conflict during decision making."""
        provider = create_provider_scenario_2()
        root_package = provider.get_package_by_name("root")

        result = solve_dependencies(provider, root_package, Version("1.0.0"))

        assert result.success is True
        assert result.solution is not None

        # Check that we get a valid solution (foo 1.0.0 avoids conflict with bar)
        solution_dict = {}
        for assignment in result.solution.get_all_assignments():
            solution_dict[assignment.package.name] = str(assignment.version)

        # The resolver should choose foo 1.0.0 to avoid the conflict
        # that would occur if foo 1.1.0 was chosen (which requires bar >= 2.0.0)
        assert solution_dict["root"] == "1.0.0"
        assert solution_dict["foo"] == "1.0.0"
        assert solution_dict["bar"] in ["1.0.0", "1.1.0"]

    def test_conflict_resolution(self):
        """Test conflict resolution."""
        provider = create_provider_scenario_3()
        root_package = provider.get_package_by_name("root")

        result = solve_dependencies(provider, root_package, Version("1.0.0"))

        assert result.success is True
        assert result.solution is not None

        # Check expected solution
        solution_dict = {}
        for assignment in result.solution.get_all_assignments():
            solution_dict[assignment.package.name] = str(assignment.version)

        # Should choose foo 2.0.0 (since root requires foo > 1.0.0)
        assert solution_dict["root"] == "1.0.0"
        assert solution_dict["foo"] == "2.0.0"
        assert solution_dict["bar"] == "1.0.0"

    def test_partial_satisfier(self):
        """Test conflict with partial satisfier."""
        provider = create_provider_partial_satisfier()
        root_package = provider.get_package_by_name("root")

        result = solve_dependencies(provider, root_package, Version("1.0.0"))

        assert result.success is True
        assert result.solution is not None

        # Check that we get a valid solution
        solution_dict = {}
        for assignment in result.solution.get_all_assignments():
            solution_dict[assignment.package.name] = str(assignment.version)

        # The resolver should find a solution that satisfies all constraints
        assert solution_dict["root"] == "1.0.0"
        assert solution_dict["foo"] == "1.0.0"
        assert solution_dict["bar"] == "1.0.0"
        assert solution_dict["left"] == "1.0.0"
        assert solution_dict["right"] == "1.0.0"
        assert solution_dict["shared"] == "2.0.0"  # Upgraded to satisfy left
        assert solution_dict["target"] == "2.0.0"  # Upgraded to satisfy right

    def test_double_choices(self):
        """Test double choices scenario."""
        provider = create_provider_double_choices()
        root_package = provider.get_package_by_name("root")

        result = solve_dependencies(provider, root_package, Version("1.0.0"))

        assert result.success is True
        assert result.solution is not None

        # Check expected solution
        solution_dict = {}
        for assignment in result.solution.get_all_assignments():
            solution_dict[assignment.package.name] = str(assignment.version)

        expected = {
            "root": "1.0.0",
            "a": "1.0.0",
            "b": "1.0.0",
            "c": "1.0.0",
            "d": "1.0.0",
        }

        assert solution_dict == expected

    def test_confusing_with_lots_of_holes(self):
        """Test confusing scenario with version holes."""
        provider = SimpleDependencyProvider()

        # Add packages
        root = provider.add_package("root", is_root=True)
        a = provider.add_package("a")
        b = provider.add_package("b")

        # Add versions with gaps
        provider.add_version(root, Version("1.0.0"))
        provider.add_version(a, Version("1.0.0"))
        provider.add_version(a, Version("3.0.0"))  # Gap: no 2.0.0
        provider.add_version(b, Version("1.0.0"))
        provider.add_version(b, Version("2.0.0"))

        # Dependencies that create complex constraints
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(a, VersionRange(Version("1.0.0"), Version("4.0.0"))),
        )
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(b, VersionRange(Version("1.0.0"), Version("3.0.0"))),
        )

        # a 3.0.0 depends on b < 2.0.0
        provider.add_dependency(
            a,
            Version("3.0.0"),
            Dependency(b, VersionRange(None, Version("2.0.0"), True, False)),
        )

        root_package = provider.get_package_by_name("root")
        result = solve_dependencies(provider, root_package, Version("1.0.0"))

        assert result.success is True
        assert result.solution is not None

        # Check that we get a valid solution
        solution_dict = {}
        for assignment in result.solution.get_all_assignments():
            solution_dict[assignment.package.name] = str(assignment.version)

        # Should find a solution avoiding the version constraints
        assert solution_dict["root"] == "1.0.0"
        # Either a 1.0.0 or a 3.0.0 with appropriate b version
        if solution_dict["a"] == "3.0.0":
            assert solution_dict["b"] == "1.0.0"  # b < 2.0.0 required by a 3.0.0
        else:
            assert solution_dict["a"] == "1.0.0"
            assert solution_dict["b"] in ["1.0.0", "2.0.0"]


class TestPubGrubFailureCases:
    """Test cases that should fail to find a solution."""

    def test_unsolvable_conflict(self):
        """Test a case with no possible solution."""
        provider = SimpleDependencyProvider()

        # Add packages
        root = provider.add_package("root", is_root=True)
        a = provider.add_package("a")
        b = provider.add_package("b")

        # Add versions
        provider.add_version(root, Version("1.0.0"))
        provider.add_version(a, Version("1.0.0"))
        provider.add_version(b, Version("1.0.0"))
        provider.add_version(b, Version("2.0.0"))

        # Create impossible constraints
        # root depends on a
        provider.add_dependency(
            root, Version("1.0.0"), Dependency(a, VersionRange(Version("1.0.0"), None))
        )

        # a depends on b >= 2.0.0
        provider.add_dependency(
            a, Version("1.0.0"), Dependency(b, VersionRange(Version("2.0.0"), None))
        )

        # root also depends on b < 2.0.0 (conflict!)
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(b, VersionRange(None, Version("2.0.0"), True, False)),
        )

        root_package = provider.get_package_by_name("root")
        result = solve_dependencies(provider, root_package, Version("1.0.0"))

        assert result.success is False
        assert result.solution is None
        assert result.error is not None


class TestPubGrubRegressionTests:
    """Additional test cases matching Rust implementation edge cases."""

    def test_depend_on_self_success(self):
        """Test that packages can depend on themselves when constraints are satisfiable."""
        provider = SimpleDependencyProvider()

        # Add package
        a = provider.add_package("a")

        # Add versions
        provider.add_version(a, Version("1.0.0"))

        # a 1.0.0 depends on a (any version) - this should work
        provider.add_dependency(
            a,
            Version("1.0.0"),
            Dependency(a, VersionRange(Version("1.0.0"), None)),
        )

        result = solve_dependencies(provider, a, Version("1.0.0"))

        assert result.success is True
        assert result.solution is not None

        # Check expected solution
        solution_dict = {}
        for assignment in result.solution.get_all_assignments():
            solution_dict[assignment.package.name] = str(assignment.version)

        assert solution_dict == {"a": "1.0.0"}

    def test_depend_on_self_failure(self):
        """Test that packages fail when self-dependency constraints are unsatisfiable."""
        provider = SimpleDependencyProvider()

        # Add package
        a = provider.add_package("a")

        # Add versions
        provider.add_version(a, Version("1.0.0"))
        provider.add_version(a, Version("2.0.0"))

        # a 1.0.0 depends on a 2.0.0 (impossible since we're selecting a 1.0.0)
        provider.add_dependency(
            a,
            Version("1.0.0"),
            Dependency(
                a, VersionRange(Version("2.0.0"), Version("2.0.0"), True, True)
            ),
        )

        result = solve_dependencies(provider, a, Version("1.0.0"))

        assert result.success is False
        assert result.solution is None
        assert result.error is not None

    def test_same_result_on_repeated_runs(self):
        """Test that the resolver produces deterministic results."""
        provider = SimpleDependencyProvider()

        # Add packages
        a = provider.add_package("a")
        b = provider.add_package("b")
        c = provider.add_package("c")

        # Add versions
        provider.add_version(a, Version("1.0.0"))
        provider.add_version(b, Version("1.0.0"))
        provider.add_version(b, Version("2.0.0"))
        provider.add_version(c, Version("1.0.0"))
        provider.add_version(c, Version("2.0.0"))

        # Dependencies
        provider.add_dependency(
            a,
            Version("1.0.0"),
            Dependency(b, VersionRange(Version("1.0.0"), None)),
        )
        provider.add_dependency(
            a,
            Version("1.0.0"),
            Dependency(c, VersionRange(Version("1.0.0"), None)),
        )
        provider.add_dependency(
            b,
            Version("2.0.0"),
            Dependency(c, VersionRange(Version("1.0.0"), Version("2.0.0"))),
        )

        # Run resolution multiple times
        results = []
        for _ in range(10):
            result = solve_dependencies(provider, a, Version("1.0.0"))
            if result.success:
                solution_dict = {}
                for assignment in result.solution.get_all_assignments():
                    solution_dict[assignment.package.name] = str(assignment.version)
                results.append(solution_dict)
            else:
                results.append(None)

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, "Resolver should produce deterministic results"

    def test_should_always_find_satisfier(self):
        """Test cases where no satisfier can be found."""
        provider = SimpleDependencyProvider()

        # Add packages
        a = provider.add_package("a")
        b = provider.add_package("b")

        # Add versions
        provider.add_version(a, Version("1.0.0"))
        # Note: b has no versions

        # a depends on b (impossible since b has no versions)
        provider.add_dependency(
            a,
            Version("1.0.0"),
            Dependency(b, VersionRange(Version("1.0.0"), None)),
        )

        result = solve_dependencies(provider, a, Version("1.0.0"))

        assert result.success is False
        assert result.solution is None
        assert result.error is not None

    def test_complex_version_constraints(self):
        """Test complex version constraints similar to Rust implementation."""
        provider = SimpleDependencyProvider()

        # Add packages
        root = provider.add_package("root", is_root=True)
        foo = provider.add_package("foo")
        bar = provider.add_package("bar")

        # Add versions with gaps (like Rust test)
        provider.add_version(root, Version("1.0.0"))
        provider.add_version(foo, Version("1.0.0"))
        provider.add_version(foo, Version("2.0.0"))
        provider.add_version(foo, Version("3.0.0"))
        provider.add_version(foo, Version("4.0.0"))
        provider.add_version(foo, Version("5.0.0"))
        # No bar versions initially

        # Root depends on foo (any version)
        provider.add_dependency(
            root,
            Version("1.0.0"),
            Dependency(foo, VersionRange(Version("1.0.0"), None)),
        )

        # All foo versions depend on bar (which doesn't exist)
        for version in ["1.0.0", "2.0.0", "3.0.0", "4.0.0", "5.0.0"]:
            provider.add_dependency(
                foo,
                Version(version),
                Dependency(bar, VersionRange(Version("1.0.0"), None)),
            )

        result = solve_dependencies(provider, root, Version("1.0.0"))

        assert result.success is False
        assert result.solution is None
        assert result.error is not None
        assert "conflict" in result.error.lower() or "fail" in result.error.lower()

    def test_missing_dependency(self):
        """Test case where a required dependency doesn't exist."""
        provider = SimpleDependencyProvider()

        # Add packages
        root = provider.add_package("root", is_root=True)
        a = provider.add_package("a")
        # Note: package 'b' is not added

        # Add versions
        provider.add_version(root, Version("1.0.0"))
        provider.add_version(a, Version("1.0.0"))

        # Create dependency on non-existent package
        provider.add_dependency(
            root, Version("1.0.0"), Dependency(a, VersionRange(Version("1.0.0"), None))
        )

        # a depends on non-existent package b
        b_package = Package("b")  # Create package reference but don't add to provider
        provider.add_dependency(
            a,
            Version("1.0.0"),
            Dependency(b_package, VersionRange(Version("1.0.0"), None)),
        )

        root_package = provider.get_package_by_name("root")
        result = solve_dependencies(provider, root_package, Version("1.0.0"))

        assert result.success is False
        assert result.solution is None
        assert result.error is not None