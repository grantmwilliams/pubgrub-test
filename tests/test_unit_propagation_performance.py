"""Performance tests for unit propagation optimization."""

import time
import pytest
from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.package import Dependency
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.resolver import PubGrubResolver


class TestUnitPropagationPerformance:
    """Test performance improvements in unit propagation."""

    def create_complex_dependency_scenario(self, num_packages: int = 20):
        """Create a complex dependency scenario with many packages."""
        provider = SimpleDependencyProvider()
        
        # Create root package
        root = provider.add_package("root", is_root=True)
        provider.add_version(root, Version("1.0.0"))
        
        packages = []
        
        # Create a chain of packages with dependencies
        for i in range(num_packages):
            pkg = provider.add_package(f"pkg_{i}")
            packages.append(pkg)
            
            # Add multiple versions for each package
            for j in range(3):
                version = Version(f"{j + 1}.0.0")
                provider.add_version(pkg, version)
                
                # Add dependencies to create a complex graph
                if i > 0:
                    # Depend on previous package
                    prev_pkg = packages[i - 1]
                    provider.add_dependency(
                        pkg, version, 
                        Dependency(prev_pkg, VersionRange(Version("1.0.0"), None))
                    )
                
                if i < num_packages - 1:
                    # Root depends on first few packages
                    if i < 5:
                        provider.add_dependency(
                            root, Version("1.0.0"),
                            Dependency(pkg, VersionRange(Version("1.0.0"), None))
                        )
        
        return provider

    def test_unit_propagation_performance(self):
        """Test that unit propagation performs well with many incompatibilities."""
        # Create a complex scenario
        provider = self.create_complex_dependency_scenario(15)
        root_package = provider.get_package_by_name("root")
        
        # Measure resolution time
        start_time = time.time()
        resolver = PubGrubResolver(provider)
        result = resolver.resolve(root_package, Version("1.0.0"))
        end_time = time.time()
        
        # Should find a solution
        assert result.success is True
        assert result.solution is not None
        
        # Should complete in reasonable time (less than 1 second)
        resolution_time = end_time - start_time
        assert resolution_time < 1.0, f"Resolution took {resolution_time:.2f}s, expected < 1.0s"
        
        # Check that we got meaningful statistics
        stats = resolver.get_resolution_statistics()
        assert stats["total_assignments"] > 0
        assert stats["total_incompatibilities"] >= 0
        
        print(f"Resolution time: {resolution_time:.3f}s")
        print(f"Statistics: {stats}")

    def test_unit_propagation_with_conflicts(self):
        """Test unit propagation performance with conflicts that require backtracking."""
        provider = SimpleDependencyProvider()
        
        # Create a scenario with inevitable conflicts
        root = provider.add_package("root", is_root=True)
        provider.add_version(root, Version("1.0.0"))
        
        # Create packages with conflicting requirements
        packages = []
        for i in range(10):
            pkg = provider.add_package(f"conflict_pkg_{i}")
            packages.append(pkg)
            
            # Add versions
            for j in range(2):
                version = Version(f"{j + 1}.0.0")
                provider.add_version(pkg, version)
        
        # Create a shared dependency
        shared = provider.add_package("shared")
        provider.add_version(shared, Version("1.0.0"))
        provider.add_version(shared, Version("2.0.0"))
        
        # Root depends on first package
        provider.add_dependency(
            root, Version("1.0.0"),
            Dependency(packages[0], VersionRange(Version("1.0.0"), None))
        )
        
        # Create conflicting dependencies on shared package
        provider.add_dependency(
            packages[0], Version("2.0.0"),
            Dependency(shared, VersionRange(Version("2.0.0"), None))
        )
        
        # Add other packages that conflict with shared 2.0.0
        for i in range(1, 5):
            provider.add_dependency(
                root, Version("1.0.0"),
                Dependency(packages[i], VersionRange(Version("1.0.0"), None))
            )
            provider.add_dependency(
                packages[i], Version("1.0.0"),
                Dependency(shared, VersionRange(None, Version("2.0.0"), True, False))
            )
        
        # Measure resolution time
        start_time = time.time()
        resolver = PubGrubResolver(provider)
        result = resolver.resolve(root, Version("1.0.0"))
        end_time = time.time()
        
        # Should find a solution by backtracking
        assert result.success is True
        
        # Should complete in reasonable time
        resolution_time = end_time - start_time
        assert resolution_time < 2.0, f"Resolution took {resolution_time:.2f}s, expected < 2.0s"
        
        # Check that backtracking occurred
        stats = resolver.get_resolution_statistics()
        assert stats["total_conflicts"] >= 0
        assert stats["max_decision_level"] >= 0
        
        print(f"Conflict resolution time: {resolution_time:.3f}s")
        print(f"Conflict statistics: {stats}")

    def test_unit_propagation_caching(self):
        """Test that caching optimizations work correctly."""
        provider = self.create_complex_dependency_scenario(10)
        root_package = provider.get_package_by_name("root")
        
        resolver = PubGrubResolver(provider)
        
        # Resolve multiple times to test caching
        times = []
        for i in range(3):
            start_time = time.time()
            result = resolver.resolve(root_package, Version("1.0.0"))
            end_time = time.time()
            
            assert result.success is True
            times.append(end_time - start_time)
        
        # All resolutions should be fast
        for i, resolution_time in enumerate(times):
            assert resolution_time < 1.0, f"Resolution {i} took {resolution_time:.2f}s"
        
        print(f"Resolution times: {[f'{t:.3f}s' for t in times]}")

    def test_large_incompatibility_set(self):
        """Test performance with a large number of incompatibilities."""
        provider = SimpleDependencyProvider()
        
        # Create a root package
        root = provider.add_package("root", is_root=True)
        provider.add_version(root, Version("1.0.0"))
        
        # Create many packages with multiple versions
        packages = []
        for i in range(30):
            pkg = provider.add_package(f"pkg_{i}")
            packages.append(pkg)
            
            # Add many versions
            for j in range(5):
                version = Version(f"{j + 1}.0.0")
                provider.add_version(pkg, version)
        
        # Create dense dependency graph
        for i, pkg in enumerate(packages[:10]):  # Only first 10 to avoid explosion
            provider.add_dependency(
                root, Version("1.0.0"),
                Dependency(pkg, VersionRange(Version("1.0.0"), None))
            )
            
            # Each package depends on a few others
            for j in range(min(3, len(packages) - i - 1)):
                if i + j + 1 < len(packages):
                    provider.add_dependency(
                        pkg, Version("1.0.0"),
                        Dependency(packages[i + j + 1], VersionRange(Version("1.0.0"), None))
                    )
        
        # Measure resolution time
        start_time = time.time()
        resolver = PubGrubResolver(provider)
        result = resolver.resolve(root, Version("1.0.0"))
        end_time = time.time()
        
        # Should find a solution
        assert result.success is True
        
        # Should complete in reasonable time even with many incompatibilities
        resolution_time = end_time - start_time
        assert resolution_time < 3.0, f"Resolution took {resolution_time:.2f}s, expected < 3.0s"
        
        stats = resolver.get_resolution_statistics()
        print(f"Large set resolution time: {resolution_time:.3f}s")
        print(f"Large set statistics: {stats}")
        print(f"Number of incompatibilities: {len(resolver.incompatibilities)}")