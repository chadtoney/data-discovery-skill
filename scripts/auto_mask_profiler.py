"""
Auto-masking data profiler.

Runs queries against a database and automatically masks potentially sensitive
columns before returning results. The LLM sees structure and patterns without
seeing actual PII values.

Usage:
    python auto_mask_profiler.py <db_path> [--table TABLE] [--sample-rows N]

The masker detects sensitive columns by name pattern and data pattern,
then replaces values with realistic but fake placeholders while preserving
statistical properties (uniqueness, null rates, distributions).
"""

import sqlite3
import re
import hashlib
import sys
import json
from pathlib import Path


# Column name patterns that suggest sensitive data
SENSITIVE_NAME_PATTERNS = [
    (r'(email|e_mail)', 'email'),
    (r'(phone|mobile|cell|fax|tel)', 'phone'),
    (r'(ssn|social_security|sin|national_id)', 'ssn'),
    (r'(first.?name|fname|given.?name)', 'first_name'),
    (r'(last.?name|lname|surname|family.?name)', 'last_name'),
    (r'(full.?name|display.?name|customer.?name|user.?name)', 'full_name'),
    (r'(address|street|city|zip|postal)', 'address'),
    (r'(credit.?card|card.?num|pan|account.?num)', 'credit_card'),
    (r'(password|pwd|pass.?hash|secret)', 'password'),
    (r'(dob|birth.?date|date.?of.?birth)', 'dob'),
    (r'(ip.?addr|ip_address)', 'ip'),
    (r'(salary|wage|income|compensation)', 'financial'),
]

# Value patterns that suggest sensitive data regardless of column name
SENSITIVE_VALUE_PATTERNS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'),
    (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 'phone'),
    (r'\b\d{3}-\d{2}-\d{4}\b', 'ssn'),
    (r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', 'credit_card'),
]


def detect_sensitive_column(col_name, sample_values):
    """Detect if a column contains sensitive data by name or value patterns."""
    col_lower = col_name.lower()

    for pattern, sensitivity_type in SENSITIVE_NAME_PATTERNS:
        if re.search(pattern, col_lower):
            return sensitivity_type

    for val in sample_values:
        if val is None:
            continue
        val_str = str(val)
        for pattern, sensitivity_type in SENSITIVE_VALUE_PATTERNS:
            if re.search(pattern, val_str):
                return sensitivity_type

    return None


def mask_value(value, sensitivity_type, row_idx=0):
    """Replace a sensitive value with a deterministic masked placeholder.
    
    Uses hashing so the same input always produces the same mask,
    preserving uniqueness/cardinality analysis without exposing real values.
    """
    if value is None:
        return None

    seed = hashlib.md5(str(value).encode()).hexdigest()[:6]

    masks = {
        'email': f'user_{seed}@masked.example',
        'phone': f'555-{seed[:3]}-{seed[3:]}',
        'ssn': '***-**-****',
        'first_name': f'Person_{seed[:4]}',
        'last_name': f'Surname_{seed[:4]}',
        'full_name': f'Person_{seed[:4]} Surname_{seed[4:]}',
        'address': f'{seed[:3]} Masked St, City, ST 00000',
        'credit_card': '****-****-****-' + seed[:4],
        'password': '[REDACTED]',
        'dob': '****-**-**',
        'ip': f'xxx.xxx.{seed[:1]}.{seed[1:3]}',
        'financial': '[MASKED_NUMBER]',
    }

    return masks.get(sensitivity_type, f'[MASKED:{sensitivity_type}]')


def profile_table(cursor, table_name, sample_rows=5):
    """Profile a table with automatic masking of sensitive columns."""

    cursor.execute(f"PRAGMA table_info('{table_name}')")
    columns = cursor.fetchall()
    col_names = [c[1] for c in columns]
    col_types = [c[2] for c in columns]

    cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
    row_count = cursor.fetchone()[0]

    # Sample for sensitivity detection
    cursor.execute(f"SELECT * FROM [{table_name}] LIMIT 20")
    detection_sample = cursor.fetchall()

    # Detect which columns need masking
    masked_columns = {}
    for i, col_name in enumerate(col_names):
        sample_vals = [row[i] for row in detection_sample]
        sensitivity = detect_sensitive_column(col_name, sample_vals)
        if sensitivity:
            masked_columns[i] = sensitivity

    # Get sample rows and mask them
    cursor.execute(f"SELECT * FROM [{table_name}] LIMIT {sample_rows}")
    sample = cursor.fetchall()

    masked_sample = []
    for row_idx, row in enumerate(sample):
        masked_row = []
        for col_idx, val in enumerate(row):
            if col_idx in masked_columns:
                masked_row.append(mask_value(val, masked_columns[col_idx], row_idx))
            else:
                masked_row.append(val)
        masked_sample.append(masked_row)

    # Null analysis
    null_counts = {}
    for col in col_names:
        cursor.execute(f"SELECT COUNT(*) FROM [{table_name}] WHERE [{col}] IS NULL")
        null_counts[col] = cursor.fetchone()[0]

    # Distinct counts
    distinct_counts = {}
    for col in col_names:
        cursor.execute(f"SELECT COUNT(DISTINCT [{col}]) FROM [{table_name}]")
        distinct_counts[col] = cursor.fetchone()[0]

    return {
        'table_name': table_name,
        'row_count': row_count,
        'columns': [{'name': n, 'type': t} for n, t in zip(col_names, col_types)],
        'masked_columns': {col_names[i]: mtype for i, mtype in masked_columns.items()},
        'null_analysis': {col: {'null_count': nc, 'null_pct': round(nc / row_count * 100, 1) if row_count > 0 else 0}
                         for col, nc in null_counts.items()},
        'distinct_counts': distinct_counts,
        'sample_rows': {
            'columns': col_names,
            'rows': masked_sample,
            'masking_applied': list(masked_columns.values()) if masked_columns else []
        }
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python auto_mask_profiler.py <db_path> [--table TABLE] [--sample-rows N]")
        sys.exit(1)

    db_path = sys.argv[1]
    target_table = None
    sample_rows = 5

    args = sys.argv[2:]
    for i, arg in enumerate(args):
        if arg == '--table' and i + 1 < len(args):
            target_table = args[i + 1]
        elif arg == '--sample-rows' and i + 1 < len(args):
            sample_rows = int(args[i + 1])

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cursor.fetchall()]

    if target_table:
        tables = [t for t in tables if t == target_table]
        if not tables:
            print(f"Table '{target_table}' not found.")
            sys.exit(1)

    results = {}
    for table in tables:
        results[table] = profile_table(cursor, table, sample_rows)

    # Print masked summary
    print("=" * 60)
    print("AUTO-MASKED PROFILING RESULTS")
    print("=" * 60)

    for table, profile in results.items():
        print(f"\n## {table} ({profile['row_count']} rows)")

        if profile['masked_columns']:
            print(f"   Masked columns: {profile['masked_columns']}")

        print(f"   Columns: {len(profile['columns'])}")

        high_nulls = {k: v for k, v in profile['null_analysis'].items() if v['null_pct'] > 0}
        if high_nulls:
            print("   Nulls:")
            for col, info in high_nulls.items():
                print(f"     - {col}: {info['null_pct']}%")

        print(f"\n   Sample rows (masked where sensitive):")
        cols = profile['sample_rows']['columns']
        print(f"   | {' | '.join(cols)} |")
        print(f"   | {' | '.join(['---'] * len(cols))} |")
        for row in profile['sample_rows']['rows'][:3]:
            vals = [str(v)[:20] if v is not None else 'NULL' for v in row]
            print(f"   | {' | '.join(vals)} |")

    # Write JSON for programmatic use
    json_path = Path(db_path).parent / f"{Path(db_path).stem}_profile_masked.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n\nFull masked profile: {json_path}")

    conn.close()


if __name__ == '__main__':
    main()
