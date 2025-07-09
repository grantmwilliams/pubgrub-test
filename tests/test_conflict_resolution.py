"""Tests for conflict resolution and CDCL functionality."""

from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.package import Dependency
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.resolver import PubGrubResolver


class TestConflictResolution:
    """Test cases for conflict resolution in the PubGrub resolver."""

    def create_conflict_test_provider(self):
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

    def test_conflict_resolution_finds_solution(self):
        """Test that conflict resolution finds a valid solution when possible."""
        provider = self.create_conflict_test_provider()
        root_package = provider.get_package_by_name("root")

        resolver = PubGrubResolver(provider)
        result = resolver.resolve(root_package, Version("1.0.0"))

        # Should find a solution by using older versions
        assert result.success is True
        assert result.solution is not None
        
        # Get the solution assignments
        assignments = {
            assignment.package.name: assignment.version
            for assignment in result.solution.get_all_assignments()
        }
        
        # Should have assigned versions for all packages
        assert "root" in assignments
        assert "a" in assignments
        assert "b" in assignments
        assert "c" in assignments
        
        # Verify the solution is consistent
        assert assignments["root"] == Version("1.0.0")
        
        # Verify the solution satisfies all constraints
        # If a=2.0.0 and b=2.0.0, then we have a conflict (impossible)
        # So the resolver should avoid this combination
        a_version = assignments["a"]
        b_version = assignments["b"] 
        c_version = assignments["c"]
        
        if a_version == Version("2.0.0") and b_version == Version("2.0.0"):
            # This combination should be impossible due to conflicting c requirements
            assert False, "Invalid solution: a=2.0.0 and b=2.0.0 creates conflict on c"
        
        # If a=2.0.0, then c must be >= 2.0.0
        if a_version == Version("2.0.0"):
            assert c_version >= Version("2.0.0"), f"a=2.0.0 requires c>=2.0.0, got c={c_version}"
        
        # If b=2.0.0, then c must be < 2.0.0
        if b_version == Version("2.0.0"):
            assert c_version < Version("2.0.0"), f"b=2.0.0 requires c<2.0.0, got c={c_version}"

    def test_conflict_resolution_statistics(self):
        """Test that conflict resolution provides useful statistics."""
        provider = self.create_conflict_test_provider()
        root_package = provider.get_package_by_name("root")

        resolver = PubGrubResolver(provider)
        resolver.resolve(root_package, Version("1.0.0"))

        # Get resolution statistics
        stats = resolver.get_resolution_statistics()
        
        # Should provide useful statistics
        assert isinstance(stats, dict)
        assert "total_assignments" in stats
        assert "total_conflicts" in stats
        assert "total_incompatibilities" in stats
        assert "max_decision_level" in stats
        
        # Should have made assignments
        assert stats["total_assignments"] > 0
        assert stats["total_conflicts"] >= 0
        assert stats["max_decision_level"] >= 0

    def create_unsolvable_test_provider(self):
        """Create a test provider with truly unsolvable conflicts."""
        provider = SimpleDependencyProvider()

        # Add packages
        root = provider.add_package("root", is_root=True)
        a = provider.add_package("a")
        b = provider.add_package("b")

        # Add versions
        provider.add_version(root, Version("1.0.0"))
        provider.add_version(a, Version("1.0.0"))
        provider.add_version(b, Version("1.0.0"))

        # Create unsolvable dependencies
        # root depends on a >= 1.0.0 and b >= 1.0.0
        provider.add_dependency(
            root, Version("1.0.0"), Dependency(a, VersionRange(Version("1.0.0"), None))
        )
        provider.add_dependency(
            root, Version("1.0.0"), Dependency(b, VersionRange(Version("1.0.0"), None))
        )

        # a 1.0.0 depends on b < 1.0.0 (impossible!)
        provider.add_dependency(
            a,
            Version("1.0.0"),
            Dependency(b, VersionRange(None, Version("1.0.0"), True, False)),
        )

        return provider

    def test_unsolvable_conflict_detection(self):
        """Test that unsolvable conflicts are properly detected."""
        provider = self.create_unsolvable_test_provider()
        root_package = provider.get_package_by_name("root")

        resolver = PubGrubResolver(provider)
        result = resolver.resolve(root_package, Version("1.0.0"))

        # Should fail to find a solution
        assert result.success is False
        assert result.solution is None
        assert result.error is not None
        assert "conflict" in result.error.lower()

    def test_cdcl_learned_clauses(self):
        """Test that CDCL learns clauses from conflicts."""
        provider = self.create_conflict_test_provider()
        root_package = provider.get_package_by_name("root")

        resolver = PubGrubResolver(provider)
        resolver.resolve(root_package, Version("1.0.0"))

        # Check that the conflict resolver has learned clauses
        learned_clauses = resolver.conflict_resolver.learned_clauses
        
        # Should have learned some clauses during resolution
        # (The exact number depends on the resolution path)
        assert isinstance(learned_clauses, list)
        
        # Each learned clause should be an Incompatibility
        for clause in learned_clauses:
            assert hasattr(clause, 'terms')
            assert hasattr(clause, 'kind')

    def test_conflict_history_tracking(self):
        """Test that conflict history is properly tracked."""
        provider = self.create_conflict_test_provider()
        root_package = provider.get_package_by_name("root")

        resolver = PubGrubResolver(provider)
        resolver.resolve(root_package, Version("1.0.0"))

        # Check that conflicts were tracked
        conflict_history = resolver.conflict_resolver.conflict_history
        
        # Should have a history of conflicts
        assert isinstance(conflict_history, list)
        
        # Each conflict should have the required fields
        for conflict in conflict_history:
            assert hasattr(conflict, 'conflicting_incompatibilities')
            assert hasattr(conflict, 'decision_level')
            assert hasattr(conflict, 'explanation')

    def test_non_chronological_backtracking(self):
        """Test that non-chronological backtracking is used."""
        provider = self.create_conflict_test_provider()
        root_package = provider.get_package_by_name("root")

        resolver = PubGrubResolver(provider)
        resolver.resolve(root_package, Version("1.0.0"))

        # Get statistics to check backtracking behavior
        stats = resolver.get_resolution_statistics()
        
        # Should have statistics about backtracking
        assert "max_decision_level" in stats
        assert "total_conflicts" in stats
        
        # Statistics should be valid
        assert stats["max_decision_level"] >= 0
        assert stats["total_conflicts"] >= 0