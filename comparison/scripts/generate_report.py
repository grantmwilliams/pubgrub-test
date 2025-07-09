#!/usr/bin/env -S uv run --script

import json
import sys
from pathlib import Path
from datetime import datetime

def generate_html_report(comparison_results, output_file):
    """Generate an HTML report from comparison results"""
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>PubGrub Implementation Comparison Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .scenario {{ margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }}
        .scenario-header {{ background-color: #f8f8f8; padding: 10px; border-bottom: 1px solid #ddd; }}
        .scenario-content {{ padding: 15px; }}
        .success {{ color: #2e7d32; }}
        .failure {{ color: #c62828; }}
        .mismatch {{ color: #f57c00; }}
        .performance {{ background-color: #e3f2fd; padding: 10px; border-radius: 3px; margin: 10px 0; }}
        .code {{ background-color: #f5f5f5; padding: 10px; border-radius: 3px; font-family: monospace; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .metric {{ display: inline-block; margin: 5px 15px 5px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>PubGrub Implementation Comparison Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Total scenarios tested: {len(comparison_results)}</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
"""
    
    # Calculate summary statistics
    total_scenarios = len(comparison_results)
    agreements = sum(1 for r in comparison_results if r['agreement']['success_match'])
    both_succeeded = sum(1 for r in comparison_results if r['agreement']['both_succeeded'])
    both_failed = sum(1 for r in comparison_results if r['agreement']['both_failed'])
    
    python_total_time = sum(r['performance']['python_runtime_ms'] for r in comparison_results)
    rust_total_time = sum(r['performance']['rust_runtime_ms'] for r in comparison_results)
    
    avg_speedup = sum(r['performance']['speedup_factor'] for r in comparison_results if r['performance']['speedup_factor'] > 0) / max(1, sum(1 for r in comparison_results if r['performance']['speedup_factor'] > 0))
    
    html_content += f"""
        <div class="metric">Agreement Rate: {agreements}/{total_scenarios} ({agreements/total_scenarios*100:.1f}%)</div>
        <div class="metric">Both Succeeded: {both_succeeded}</div>
        <div class="metric">Both Failed: {both_failed}</div>
        <div class="metric">Python Total Time: {python_total_time:.1f}ms</div>
        <div class="metric">Rust Total Time: {rust_total_time:.1f}ms</div>
        <div class="metric">Average Speedup: {avg_speedup:.2f}x</div>
    </div>
    
    <h2>Detailed Results</h2>
"""
    
    for result in comparison_results:
        scenario_name = result['scenario']
        description = result.get('description', '')
        agreement = result['agreement']
        
        # Determine status class
        if agreement['success_match']:
            status_class = "success" if agreement['both_succeeded'] else "failure"
            status_text = "✓ Agreement" if agreement['both_succeeded'] else "✓ Both Failed"
        else:
            status_class = "mismatch"
            status_text = "✗ Mismatch"
        
        html_content += f"""
    <div class="scenario">
        <div class="scenario-header">
            <h3>{scenario_name} <span class="{status_class}">{status_text}</span></h3>
            {f'<p>{description}</p>' if description else ''}
        </div>
        <div class="scenario-content">
            <div class="performance">
                <strong>Performance:</strong>
                Python: {result['performance']['python_runtime_ms']:.1f}ms | 
                Rust: {result['performance']['rust_runtime_ms']:.1f}ms |
                Speedup: {result['performance']['speedup_factor']:.2f}x
            </div>
            
            <table>
                <tr><th>Implementation</th><th>Success</th><th>Solution</th><th>Error</th></tr>
                <tr>
                    <td>Python</td>
                    <td class="{'success' if result['python']['success'] else 'failure'}">
                        {'✓' if result['python']['success'] else '✗'}
                    </td>
                    <td><div class="code">{json.dumps(result['python'].get('solution'), indent=2) if result['python'].get('solution') else 'None'}</div></td>
                    <td><div class="code">{result['python'].get('error', 'None')}</div></td>
                </tr>
                <tr>
                    <td>Rust</td>
                    <td class="{'success' if result['rust']['success'] else 'failure'}">
                        {'✓' if result['rust']['success'] else '✗'}
                    </td>
                    <td><div class="code">{json.dumps(result['rust'].get('solution'), indent=2) if result['rust'].get('solution') else 'None'}</div></td>
                    <td><div class="code">{result['rust'].get('error', 'None')}</div></td>
                </tr>
            </table>
        </div>
    </div>
"""
    
    html_content += """
</body>
</html>
"""
    
    with open(output_file, 'w') as f:
        f.write(html_content)

def generate_csv_report(comparison_results, output_file):
    """Generate a CSV report from comparison results"""
    import csv
    
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = [
            'scenario', 'description', 'python_success', 'rust_success', 
            'agreement', 'python_runtime_ms', 'rust_runtime_ms', 'speedup_factor',
            'python_error', 'rust_error'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in comparison_results:
            writer.writerow({
                'scenario': result['scenario'],
                'description': result.get('description', ''),
                'python_success': result['python']['success'],
                'rust_success': result['rust']['success'],
                'agreement': result['agreement']['success_match'],
                'python_runtime_ms': result['performance']['python_runtime_ms'],
                'rust_runtime_ms': result['performance']['rust_runtime_ms'],
                'speedup_factor': result['performance']['speedup_factor'],
                'python_error': result['python'].get('error', ''),
                'rust_error': result['rust'].get('error', '')
            })

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_report.py <comparison_results.json> [output_prefix]")
        sys.exit(1)
    
    results_file = sys.argv[1]
    output_prefix = sys.argv[2] if len(sys.argv) > 2 else "comparison_report"
    
    # Load comparison results
    with open(results_file, 'r') as f:
        comparison_results = json.load(f)
    
    # Generate reports
    html_file = f"{output_prefix}.html"
    csv_file = f"{output_prefix}.csv"
    
    generate_html_report(comparison_results, html_file)
    generate_csv_report(comparison_results, csv_file)
    
    print(f"Reports generated:")
    print(f"  HTML: {html_file}")
    print(f"  CSV: {csv_file}")

if __name__ == "__main__":
    main()