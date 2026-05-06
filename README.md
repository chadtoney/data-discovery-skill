# Data Discovery Skill

A [GitHub Copilot skill](https://docs.github.com/en/copilot) for discovering, profiling, and documenting database schemas — with data modeling recommendations.

## What it does

- **Schema Discovery** — Lists tables, columns, keys, indexes, and relationships
- **Data Profiling** — Row counts, null percentages, distinct values, sample rows, value distributions
- **Documentation** — Generates clean markdown (or .docx) database documentation
- **Data Modeling** — Suggests star schema, snowflake, and dimensional modeling designs
- **Flexible Connectivity** — Works with SQL Server, PostgreSQL, MySQL, SQLite, or any database accessible via connection string

## Installation

### GitHub Copilot CLI

```bash
/install-skill https://github.com/chadtoney/data-discovery-skill
```

### Manual

Copy the `SKILL.md` and `references/` folder into your Copilot skills directory:
```
~/.copilot/skills/data-discovery/
├── SKILL.md
└── references/
    └── query-patterns.md
```

## Usage

Once installed, the skill triggers automatically when you ask things like:

- "Help me understand this database"
- "What tables are in this schema?"
- "Profile the orders table"
- "Document this database for my team"
- "Suggest a star schema for our analytics layer"
- "Show me the relationships between these tables"

## License

MIT
