#!/usr/bin/env bash
set -euo pipefail

# Load test for UEBA system
# Expects: docker-compose up -d (all services running)

echo "=== UEBA Load Test ==="
echo "Starting Locust with 50 users, 5 spawn-rate, 60s runtime"

locust -f locustfile.py \
    --headless \
    -u 50 \
    -r 5 \
    --run-time 60s \
    --host http://localhost:8001 \
    --csv data/load_test_results \
    --html data/load_test_report.html \
    2>&1 | tee data/load_test_output.log

echo ""
echo "=== Results ==="
python3 -c "
import json, csv, re

# Parse locust stats from CSV
try:
    with open('data/load_test_results_stats.csv') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    total_rps = sum(float(r.get('Requests/s', 0)) for r in rows)
    total_reqs = sum(int(r.get('Request Count', 0)) for r in rows)
    failures = sum(int(r.get('Failure Count', 0)) for r in rows)

    results = {
        'total_requests': total_reqs,
        'total_failures': failures,
        'avg_rps': round(total_rps, 2),
        'target_met': total_rps >= 1000,
    }
    print(json.dumps(results, indent=2))

    if results['target_met']:
        echo 'PASS: >= 1000 req/s achieved'
    else:
        echo 'WARNING: target 1000 req/s not met'
        echo 'Consider: increasing replicas, optimizing ES queries'
except Exception as e:
    print(f'Error parsing results: {e}')
" 2>&1
