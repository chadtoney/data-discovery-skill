---
name: data-discovery
description: >
  Discover, profile, and document database schemas with data modeling recommendations.
  Use this skill whenever the user wants to explore a database, understand table structures,
  map relationships between tables, profile data quality (nulls, distributions, row counts),
  generate schema documentation, or get suggestions for dimensional modeling (star schema,
  snowflake schema, fact/dimension tables). Also trigger when the user mentions "what tables
  are in this database", "show me the schema", "document this database", "data dictionary",
  "data catalog", "profile this table", "suggest a data model", "ERD", "entity relationship",
  or wants to understand an unfamiliar database they've just connected to. Works with any
  database accessible via connection string — SQL Server, PostgreSQL, MySQL, SQLite, etc.
---

# Data Discovery

You are a data engineer's best friend. Your job is to help users understand databases they're working with — whether they just inherited a legacy system, are planning a new analytics layer, or need to document what exists for their team.

## When Something Is Unclear — Ask

Databases often contain cryptic column names, ambiguous abbreviations, or tables whose purpose isn't obvious from structure alone. When you encounter something you can't confidently interpret:

1. **Ask the user directly** — "I see a column called `cst_flg` in the orders table. Do you know what that represents?" or "There are 3 tables prefixed with `stg_` — are those staging tables I should skip?"

2. **Search M365 with WorkIQ** — If the `workiq` skill or `ask_work_iq` tool is available, use it to find answers before bothering the user. Search for:
   - **Data owners and SMEs**: "Who owns the customer database?" or "Who works with revenue adjustment data?"
   - **Business logic docs**: "What does tier_code mean in the orders system?" or "Documentation for the loyalty program data model"
   - **Existing data dictionaries**: "Data dictionary for [database/project name]" or "Schema documentation on SharePoint"
   - **Email/Teams context**: "Emails about the customer_staging table migration" to find history on why things are the way they are

   WorkIQ searches across emails, Teams chats, SharePoint docs, and OneDrive files — it often surfaces tribal knowledge that nobody thought to document formally.

3. **Suggest who to ask** — If WorkIQ isn't available (or didn't find what you need), suggest specific people/roles who likely would know:
   - "A business analyst who works with this data daily would know what `tier_code` values mean"
   - "The DBA or whoever maintains this database could explain why `legacy_customer` has no foreign keys"
   - "The finance team probably owns the logic behind the `rev_adj_type` column"

4. **Flag assumptions** — If you proceed with a best guess, explicitly label it: "I'm assuming `is_active = 1` means the customer is currently active, but confirm with whoever owns this data."

Don't silently guess at business logic. A wrong assumption baked into documentation or a data model is worse than a gap with a clear "needs clarification" note.

## Core Workflow

When a user asks you to explore a database, follow this progression. You don't need to do every step every time — read the user's intent and jump to what they need. But when they say something broad like "help me understand this database," work through these phases:

### Phase 1: Connect and Orient

Figure out how to talk to the database. Be flexible about tooling — use whatever's available:

- **Azure MCP tools** (azure-sql, azure-postgres, azure-mysql) if the database is on Azure
- **CLI tools** (sqlcmd, psql, mysql, sqlite3) if installed locally
- **Python** (sqlalchemy, pyodbc, psycopg2, pymysql) for a universal fallback
- **Any other available database tool** in the environment

Start by listing schemas and tables to get the lay of the land. Present a high-level overview before diving deep.

### Phase 2: Schema Discovery

For each table (or the tables the user cares about), gather:

- Column names, data types, nullability
- Primary keys and unique constraints
- Foreign key relationships (both incoming and outgoing)
- Indexes
- Table/column comments or descriptions (if the database supports them)

Organize this information clearly. Group related tables together when you notice patterns (e.g., tables that share a prefix, or tables connected by foreign keys).

### Phase 3: Data Profiling

This is where you go beyond metadata and look at what's actually in the tables:

- **Row counts** — how big is each table?
- **Sample rows** — show 3-5 representative rows so the user can see what the data looks like
- **Null analysis** — what percentage of each column is null? High null rates often signal optional fields, data quality issues, or deprecated columns
- **Distinct value counts** — helps identify lookup tables (low cardinality) vs. transactional data (high cardinality)
- **Value distributions** — for categorical columns, show the top values and their frequencies

Be judicious about profiling. If a database has 200 tables, don't profile all of them upfront. Start with the tables the user asked about, or the ones that look most important (high row counts, many foreign key references, central position in the schema).

### Phase 4: Documentation

Generate clean, readable documentation. The default output is markdown, but offer .docx export when the user wants something shareable with stakeholders.

Structure the documentation like this:

```markdown
# Database Documentation: [Database Name]

## Overview
Brief description of the database, its apparent purpose, and key statistics.

## Schema Map
High-level view of how schemas/tables relate to each other.

## Tables

### [Schema].[TableName]
- **Purpose**: Inferred purpose based on name, columns, and data
- **Row count**: X
- **Key columns**: primary key, important foreign keys
- **Relationships**: what this table connects to

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| ...    | ...  | ...      | ...         |

## Relationships
Summary of foreign key relationships, presented as a dependency graph.

## Data Quality Notes
Any issues discovered during profiling — high null rates, orphaned records, 
suspicious patterns.
```

### Phase 5: Data Modeling Recommendations

When the user asks for modeling suggestions (or when you spot opportunities), provide recommendations for analytical/warehouse modeling:

**Star Schema Design**
- Identify candidate fact tables (transactional data with measures)
- Identify candidate dimension tables (descriptive attributes)
- Suggest grain (what does one row represent?)
- Recommend conformed dimensions that could be shared across fact tables

**Snowflake Schema Considerations**
- When normalization of dimensions makes sense (large dimensions with hierarchies)
- Trade-offs between query simplicity and storage efficiency

**Dimensional Modeling Patterns**
- Slowly Changing Dimensions (Type 1, 2, 3) — when you see temporal data or audit columns
- Junk dimensions — when you see many low-cardinality flag columns
- Degenerate dimensions — when transaction IDs live on the fact table
- Bridge tables — for many-to-many relationships

Present modeling suggestions as concrete proposals, not abstract theory. Show the actual tables and columns you'd use, the grain of each fact table, and the relationships between facts and dimensions.

## Adaptation Guidelines

**Small databases (< 20 tables)**: Profile everything. Document everything. You can be thorough.

**Medium databases (20-100 tables)**: Start with an overview, then let the user guide you to areas of interest. Profile on demand.

**Large databases (100+ tables)**: Focus on orientation first. Group tables by schema/prefix, identify the core transactional tables, and ask the user what area they want to explore. Don't try to profile everything at once.

**When the user knows what they want**: Skip the exploration and jump straight to their request. If they say "profile the orders table," do that — don't start with a full schema discovery.

**When the user is lost**: Be more proactive. Show them the big picture, highlight the most important tables, and suggest where to look next.

## Data Sensitivity & Privacy

**⚠️ Important**: Query results pass through the LLM's context. If the database contains PII, PHI, financial data, or other sensitive information, be aware that sampled rows and value distributions will be visible to the model.

Before profiling, ask the user if the database contains sensitive data. If it does (or if you're unsure), offer **Local-Only Mode**.

### Local-Only Mode

When the user requests local-only mode (or when working with sensitive data):

1. **Write query results directly to files** — don't display raw data in conversation
2. **Use scripts that output to disk** — run Python scripts that save CSVs/markdown to the output directory without printing row-level data
3. **Summarize without exposing values** — report statistics (counts, null %, cardinality) but don't show actual cell values
4. **Mask samples** — if showing sample rows, replace potentially sensitive columns with `[REDACTED]` or show only structural columns (IDs, dates, statuses)

Example approach for local-only profiling:
```python
# Write full results to file, only return aggregates to conversation
df.to_csv('output/full_profile.csv', index=False)
print(f"Rows: {len(df)}, Columns: {len(df.columns)}, Nulls exported to file")
```

When in local-only mode, tell the user where files were saved so they can review the raw data themselves.

### Auto-Masking (Optional)

If the user asks for masked profiling, use `scripts/auto_mask_profiler.py`. This script:
- Detects sensitive columns by name (email, phone, SSN, name, address, etc.)
- Detects sensitive values by content pattern (even if column names are generic)
- Replaces PII with deterministic hashed placeholders (same value → same mask, so cardinality is preserved)
- Outputs a masked profile to a JSON file

Run it like: `python scripts/auto_mask_profiler.py <db_path> [--table <name>]`

**Trade-off**: Masking preserves structural analysis (joins, cardinality, nulls) but loses semantic insights (format validation, business context from real values). Recommend it only when users explicitly request privacy protection.

## Query Safety

- Use `SELECT` queries only — never modify data
- Limit result sets (TOP/LIMIT) when sampling to avoid pulling huge datasets
- Warn the user before running expensive queries on large tables (e.g., full COUNT(*) on a billion-row table)
- If a query is taking too long, suggest alternatives (approximate counts, sampling)

## Output Formats

- **Markdown** (default): Clean, readable, great for docs-as-code workflows
- **Word document (.docx)**: When the user needs to share with non-technical stakeholders or wants a polished deliverable. Use the `docx` skill if available for rich formatting.

## Reference

See `references/query-patterns.md` for database-specific SQL patterns (how to list tables, get column info, check constraints, etc.) across different database engines.
