"""
Sudoku constraint satisfaction benchmark using PubGrub resolver.

This benchmark demonstrates how the PubGrub resolver can be used to solve
constraint satisfaction problems like Sudoku by encoding the problem as
a dependency resolution scenario.
"""

import time
from typing import Optional
from dataclasses import dataclass

from pubgrub_resolver.dependency_provider import SimpleDependencyProvider
from pubgrub_resolver.package import Package, Dependency
from pubgrub_resolver.version import Version, VersionRange
from pubgrub_resolver.resolver import solve_dependencies


@dataclass
class SudokuBenchmarkResult:
    """Result of a Sudoku solving benchmark."""

    name: str
    size: int
    difficulty: str
    duration_ms: float
    success: bool
    filled_cells: int
    total_cells: int
    description: str


class SudokuSolver:
    """
    Sudoku solver using PubGrub resolver.

    Each cell is modeled as a "package" with potential values as "versions".
    Constraints prevent duplicates in rows, columns, and 3x3 boxes.
    """

    def __init__(self, size: int = 9):
        self.size = size
        self.box_size = int(size**0.5)
        self.provider = SimpleDependencyProvider()
        self.cells: dict[tuple[int, int], Package] = {}
        self.constraint_package: Optional[Package] = None

    def create_cell_packages(self) -> None:
        """Create packages for each cell in the grid."""
        for row in range(self.size):
            for col in range(self.size):
                cell_name = f"cell_{row}_{col}"
                package = self.provider.add_package(cell_name)
                self.cells[(row, col)] = package

                # Add possible values as versions
                for value in range(1, self.size + 1):
                    version = Version(f"{value}.0.0")
                    self.provider.add_version(package, version)

    def create_constraint_package(self) -> None:
        """Create a constraint package to enforce Sudoku rules."""
        self.constraint_package = self.provider.add_package("constraints", is_root=True)
        self.provider.add_version(self.constraint_package, Version("1.0.0"))

    def add_sudoku_constraints(self) -> None:
        """Add Sudoku constraints as dependencies."""
        if not self.constraint_package:
            return

        # For each cell, create constraints with other cells
        for row in range(self.size):
            for col in range(self.size):
                cell_package = self.cells[(row, col)]

                # Add dependency from constraint package to each cell
                # This ensures each cell must have a value
                self.provider.add_dependency(
                    self.constraint_package,
                    Version("1.0.0"),
                    Dependency(
                        cell_package,
                        VersionRange(
                            Version("1.0.0"), Version(f"{self.size}.0.0"), True, True
                        ),
                    ),
                )

                # Add constraints to prevent duplicates
                self._add_row_constraints(row, col)
                self._add_column_constraints(row, col)
                self._add_box_constraints(row, col)

    def _add_row_constraints(self, row: int, col: int) -> None:
        """Add constraints to prevent duplicates in the same row."""
        cell_package = self.cells[(row, col)]

        # For each value, create constraints with other cells in the same row
        for value in range(1, self.size + 1):
            version = Version(f"{value}.0.0")

            # Create a constraint package for this specific constraint
            constraint_name = f"row_{row}_value_{value}_not_col_{col}"
            constraint_pkg = self.provider.add_package(constraint_name)
            self.provider.add_version(constraint_pkg, Version("1.0.0"))

            # This cell having this value means no other cell in the row can have it
            self.provider.add_dependency(
                cell_package,
                version,
                Dependency(
                    constraint_pkg,
                    VersionRange(Version("1.0.0"), Version("1.0.0"), True, True),
                ),
            )

            # Other cells in the row cannot have this value when this constraint is active
            for other_col in range(self.size):
                if other_col != col:
                    other_cell = self.cells[(row, other_col)]
                    # If constraint is active, other cell cannot have this value
                    self.provider.add_dependency(
                        constraint_pkg,
                        Version("1.0.0"),
                        Dependency(
                            other_cell,
                            VersionRange(
                                Version(f"{value}.0.0"),
                                Version(f"{value}.0.0"),
                                False,
                                False,
                            ),
                        ),
                    )

    def _add_column_constraints(self, row: int, col: int) -> None:
        """Add constraints to prevent duplicates in the same column."""
        cell_package = self.cells[(row, col)]

        # For each value, create constraints with other cells in the same column
        for value in range(1, self.size + 1):
            version = Version(f"{value}.0.0")

            # Create a constraint package for this specific constraint
            constraint_name = f"col_{col}_value_{value}_not_row_{row}"
            constraint_pkg = self.provider.add_package(constraint_name)
            self.provider.add_version(constraint_pkg, Version("1.0.0"))

            # This cell having this value activates the constraint
            self.provider.add_dependency(
                cell_package,
                version,
                Dependency(
                    constraint_pkg,
                    VersionRange(Version("1.0.0"), Version("1.0.0"), True, True),
                ),
            )

            # Other cells in the column cannot have this value when constraint is active
            for other_row in range(self.size):
                if other_row != row:
                    other_cell = self.cells[(other_row, col)]
                    # If constraint is active, other cell cannot have this value
                    self.provider.add_dependency(
                        constraint_pkg,
                        Version("1.0.0"),
                        Dependency(
                            other_cell,
                            VersionRange(
                                Version(f"{value}.0.0"),
                                Version(f"{value}.0.0"),
                                False,
                                False,
                            ),
                        ),
                    )

    def _add_box_constraints(self, row: int, col: int) -> None:
        """Add constraints to prevent duplicates in the same 3x3 box."""
        cell_package = self.cells[(row, col)]
        box_row = (row // self.box_size) * self.box_size
        box_col = (col // self.box_size) * self.box_size

        # For each value, create constraints with other cells in the same box
        for value in range(1, self.size + 1):
            version = Version(f"{value}.0.0")

            # Create a constraint package for this specific constraint
            constraint_name = f"box_{box_row}_{box_col}_value_{value}_not_{row}_{col}"
            constraint_pkg = self.provider.add_package(constraint_name)
            self.provider.add_version(constraint_pkg, Version("1.0.0"))

            # This cell having this value activates the constraint
            self.provider.add_dependency(
                cell_package,
                version,
                Dependency(
                    constraint_pkg,
                    VersionRange(Version("1.0.0"), Version("1.0.0"), True, True),
                ),
            )

            # Other cells in the box cannot have this value when constraint is active
            for other_row in range(box_row, box_row + self.box_size):
                for other_col in range(box_col, box_col + self.box_size):
                    if other_row != row or other_col != col:
                        other_cell = self.cells[(other_row, other_col)]
                        # If constraint is active, other cell cannot have this value
                        self.provider.add_dependency(
                            constraint_pkg,
                            Version("1.0.0"),
                            Dependency(
                                other_cell,
                                VersionRange(
                                    Version(f"{value}.0.0"),
                                    Version(f"{value}.0.0"),
                                    False,
                                    False,
                                ),
                            ),
                        )

    def set_initial_values(self, puzzle: list[list[int]]) -> None:
        """Set initial values for the puzzle."""
        for row in range(self.size):
            for col in range(self.size):
                if puzzle[row][col] != 0:
                    cell_package = self.cells[(row, col)]
                    value = puzzle[row][col]

                    # Create a constraint that forces this cell to have this value
                    constraint_name = f"fixed_{row}_{col}_value_{value}"
                    constraint_pkg = self.provider.add_package(constraint_name)
                    self.provider.add_version(constraint_pkg, Version("1.0.0"))

                    # Constraint package must be active
                    self.provider.add_dependency(
                        self.constraint_package,
                        Version("1.0.0"),
                        Dependency(
                            constraint_pkg,
                            VersionRange(
                                Version("1.0.0"), Version("1.0.0"), True, True
                            ),
                        ),
                    )

                    # When active, forces the cell to have the specific value
                    self.provider.add_dependency(
                        constraint_pkg,
                        Version("1.0.0"),
                        Dependency(
                            cell_package,
                            VersionRange(
                                Version(f"{value}.0.0"),
                                Version(f"{value}.0.0"),
                                True,
                                True,
                            ),
                        ),
                    )

    def solve(self) -> Optional[list[list[int]]]:
        """Solve the Sudoku puzzle using PubGrub resolver."""
        if not self.constraint_package:
            return None

        result = solve_dependencies(
            self.provider, self.constraint_package, Version("1.0.0")
        )

        if not result.success:
            return None

        # Extract solution from assignments
        solution = [[0 for _ in range(self.size)] for _ in range(self.size)]

        for assignment in result.solution.get_all_assignments():
            package_name = assignment.package.name
            if package_name.startswith("cell_"):
                parts = package_name.split("_")
                row = int(parts[1])
                col = int(parts[2])
                value = int(str(assignment.version).split(".")[0])
                solution[row][col] = value

        return solution

    def print_grid(self, grid: list[list[int]]) -> None:
        """Print a Sudoku grid."""
        for row in range(self.size):
            if row % self.box_size == 0 and row != 0:
                print("------+-------+------")
            for col in range(self.size):
                if col % self.box_size == 0 and col != 0:
                    print("| ", end="")
                print(f"{grid[row][col] if grid[row][col] != 0 else '.'} ", end="")
            print()


class SudokuBenchmarks:
    """Benchmarks for Sudoku solving using PubGrub resolver."""

    def __init__(self):
        self.results: list[SudokuBenchmarkResult] = []

    def get_easy_puzzle(self) -> list[list[int]]:
        """Get an easy 9x9 Sudoku puzzle."""
        return [
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9],
        ]

    def get_medium_puzzle(self) -> list[list[int]]:
        """Get a medium 9x9 Sudoku puzzle."""
        return [
            [0, 0, 0, 6, 0, 0, 4, 0, 0],
            [7, 0, 0, 0, 0, 3, 6, 0, 0],
            [0, 0, 0, 0, 9, 1, 0, 8, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 5, 0, 1, 8, 0, 0, 0, 3],
            [0, 0, 0, 3, 0, 6, 0, 4, 5],
            [0, 4, 0, 2, 0, 0, 0, 6, 0],
            [9, 0, 3, 0, 0, 0, 0, 0, 0],
            [0, 2, 0, 0, 0, 0, 1, 0, 0],
        ]

    def get_simple_4x4_puzzle(self) -> list[list[int]]:
        """Get a simple 4x4 Sudoku puzzle."""
        return [[0, 0, 0, 1], [4, 0, 0, 0], [0, 0, 0, 2], [1, 0, 0, 0]]

    def benchmark_sudoku_solving(
        self, puzzle: list[list[int]], name: str, difficulty: str
    ) -> SudokuBenchmarkResult:
        """Benchmark solving a Sudoku puzzle."""
        size = len(puzzle)
        filled_cells = sum(1 for row in puzzle for cell in row if cell != 0)
        total_cells = size * size

        print(
            f"\nSolving {name} ({difficulty}) - {filled_cells}/{total_cells} cells filled:"
        )

        solver = SudokuSolver(size)
        solver.create_cell_packages()
        solver.create_constraint_package()
        solver.add_sudoku_constraints()
        solver.set_initial_values(puzzle)

        print("Initial puzzle:")
        solver.print_grid(puzzle)

        # Benchmark solving
        start_time = time.perf_counter()
        solution = solver.solve()
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000
        success = solution is not None

        if success:
            print(f"\n✅ Solved in {duration_ms:.2f}ms!")
            print("Solution:")
            solver.print_grid(solution)
        else:
            print(f"\n❌ Failed to solve in {duration_ms:.2f}ms")

        return SudokuBenchmarkResult(
            name=name,
            size=size,
            difficulty=difficulty,
            duration_ms=duration_ms,
            success=success,
            filled_cells=filled_cells,
            total_cells=total_cells,
            description=f"{size}x{size} {difficulty} puzzle ({filled_cells}/{total_cells} filled)",
        )

    def run_all_benchmarks(self) -> list[SudokuBenchmarkResult]:
        """Run all Sudoku benchmarks."""
        benchmarks = [
            # 4x4 puzzle (simpler for testing)
            lambda: self.benchmark_sudoku_solving(
                self.get_simple_4x4_puzzle(), "4x4_simple", "easy"
            ),
            # 9x9 puzzles would be too complex for the constraint encoding approach
            # The number of packages and dependencies would be enormous
            # This is more of a proof-of-concept that shows the flexibility of PubGrub
        ]

        results = []
        for benchmark in benchmarks:
            try:
                result = benchmark()
                results.append(result)
            except Exception as e:
                print(f"✗ Benchmark failed: {e}")

        return results

    def print_results(self, results: list[SudokuBenchmarkResult]):
        """Print benchmark results."""
        print("\n" + "=" * 80)
        print("SUDOKU CONSTRAINT SATISFACTION BENCHMARKS")
        print("=" * 80)
        print(
            f"{'Name':<20} {'Size':<6} {'Difficulty':<10} {'Duration (ms)':<15} {'Status':<10} {'Description'}"
        )
        print("-" * 80)

        for result in results:
            status = "SUCCESS" if result.success else "FAILED"
            print(
                f"{result.name:<20} {result.size:<6} {result.difficulty:<10} {result.duration_ms:<15.2f} "
                f"{status:<10} {result.description}"
            )

        print("-" * 80)

        # Summary
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        print("\nSUMMARY:")
        print(f"  Total benchmarks: {len(results)}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")

        if successful:
            durations = [r.duration_ms for r in successful]
            print(f"  Average duration: {sum(durations) / len(durations):.2f}ms")
            print(f"  Min duration: {min(durations):.2f}ms")
            print(f"  Max duration: {max(durations):.2f}ms")


def main():
    """Run Sudoku benchmarks."""
    print("PubGrub Sudoku Constraint Satisfaction Benchmark")
    print("=" * 50)
    print(
        "This benchmark demonstrates using PubGrub resolver for constraint satisfaction."
    )
    print("Each Sudoku cell is modeled as a package with values as versions.")
    print("Constraints prevent duplicates in rows, columns, and boxes.")
    print()
    print(
        "Note: This is a proof-of-concept. Real Sudoku solvers use more efficient algorithms."
    )

    benchmarks = SudokuBenchmarks()
    results = benchmarks.run_all_benchmarks()
    benchmarks.print_results(results)


if __name__ == "__main__":
    main()
