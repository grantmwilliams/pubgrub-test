# PubGrub Resolver Performance Benchmarks

This document tracks the performance characteristics of our PubGrub resolver implementation, comparing against baseline measurements and the reference pubgrub-rs implementation.

## Current Baseline Performance

### Version Operations
- **Version creation**: ~765 KOps/s (1.3 μs per operation)
- **Version comparison**: ~3.5 MOps/s (283 ns per operation)
- **Version range contains**: ~1.6 MOps/s (626 ns per operation)
- **Version range intersection**: ~644 KOps/s (1.55 μs per operation)

### Term Operations
- **Term creation**: ~4.6 MOps/s (215 ns per operation)
- **Term negation**: ~4.0 MOps/s (248 ns per operation)
- **Term intersection**: ~423 KOps/s (2.36 μs per operation)
- **Term satisfies check**: ~448 KOps/s (2.23 μs per operation)

### Stress Test Performance
- **Complex range intersections**: ~68 KOps/s (14.8 μs per operation)
- **Many version comparisons**: ~5 KOps/s (212 μs per operation)
- **Version parsing stress**: ~1.3 KOps/s (763 μs per operation)

## Benchmark Structure

Our benchmarks are organized into several categories:

### 1. Unit Performance Tests
- `bench_version.py`: Tests version parsing, comparison, and range operations
- `bench_term.py`: Tests term creation, intersection, and satisfies relationships

### 2. Backtracking Benchmarks (Future)
- `bench_backtracking.py`: Will test resolver performance under various backtracking scenarios
- Based on pubgrub-rs benchmarks: singletons, disjoint versions, ranges
- Variable complexity testing (5-300 packages, 200-500 versions)

### 3. Constraint Satisfaction Benchmarks (Future)
- Sudoku solving as constraint satisfaction problem
- General constraint encoding performance

## Performance Goals

Based on pubgrub-rs benchmarks, our goals are:
1. **Dependency Resolution**: Handle large package sets (300+ packages, 500+ versions)
2. **Backtracking Performance**: Efficient resolution of complex constraint scenarios
3. **Memory Usage**: Minimize memory allocations during resolution
4. **Constraint Generality**: Support non-dependency constraint problems (like Sudoku)

## Running Benchmarks

```bash
# Run all benchmarks
uv run pytest benchmarks/ --benchmark-only

# Run specific benchmark categories
uv run pytest benchmarks/bench_version.py --benchmark-only
uv run pytest benchmarks/bench_term.py --benchmark-only

# Compare performance over time
uv run pytest benchmarks/ --benchmark-only --benchmark-compare-fail=min:10%
```

## Performance Tracking

We track performance regressions by:
1. **Baseline tests**: `TestPerformanceRegression` class maintains baseline performance
2. **Benchmark comparison**: Using pytest-benchmark to compare results over time
3. **Critical path optimization**: Focus on operations used most frequently in resolution

## Known Performance Issues

1. **Negative term intersection**: Current implementation has mathematical bugs affecting performance
2. **Complex range operations**: May need optimization for large-scale scenarios
3. **Memory allocation**: Not yet optimized for minimal allocations

## Future Improvements

1. **Implement proper union operations** for version ranges
2. **Optimize term intersection** with better algorithms
3. **Add caching** for expensive operations
4. **Profile memory usage** and optimize allocations
5. **Compare against pubgrub-rs** benchmarks directly