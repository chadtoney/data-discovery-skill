# Query Patterns by Database Engine

A quick reference for the SQL needed to discover schema metadata across different database engines. The skill should detect which engine it's working with and use the appropriate patterns.

## SQL Server / Azure SQL

### List all tables
```sql
SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
FROM INFORMATION_SCHEMA.TABLES
ORDER BY TABLE_SCHEMA, TABLE_NAME;
```

### Column details
```sql
SELECT 
    c.COLUMN_NAME,
    c.DATA_TYPE,
    c.CHARACTER_MAXIMUM_LENGTH,
    c.NUMERIC_PRECISION,
    c.IS_NULLABLE,
    c.COLUMN_DEFAULT,
    ep.value AS description
FROM INFORMATION_SCHEMA.COLUMNS c
LEFT JOIN sys.extended_properties ep 
    ON ep.major_id = OBJECT_ID(c.TABLE_SCHEMA + '.' + c.TABLE_NAME)
    AND ep.minor_id = COLUMNPROPERTY(OBJECT_ID(c.TABLE_SCHEMA + '.' + c.TABLE_NAME), c.COLUMN_NAME, 'ColumnId')
    AND ep.name = 'MS_Description'
WHERE c.TABLE_SCHEMA = @schema AND c.TABLE_NAME = @table
ORDER BY c.ORDINAL_POSITION;
```

### Primary keys
```sql
SELECT kcu.COLUMN_NAME
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
    ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
WHERE tc.TABLE_SCHEMA = @schema 
    AND tc.TABLE_NAME = @table 
    AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
ORDER BY kcu.ORDINAL_POSITION;
```

### Foreign keys
```sql
SELECT 
    fk.name AS constraint_name,
    OBJECT_SCHEMA_NAME(fk.parent_object_id) AS from_schema,
    OBJECT_NAME(fk.parent_object_id) AS from_table,
    COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS from_column,
    OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS to_schema,
    OBJECT_NAME(fk.referenced_object_id) AS to_table,
    COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS to_column
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
WHERE OBJECT_SCHEMA_NAME(fk.parent_object_id) = @schema
    AND OBJECT_NAME(fk.parent_object_id) = @table;
```

### Row counts (fast approximate)
```sql
SELECT 
    s.name AS schema_name,
    t.name AS table_name,
    p.rows AS approximate_row_count
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0, 1)
ORDER BY p.rows DESC;
```

### Null percentages
```sql
SELECT 
    COUNT(*) AS total_rows,
    COUNT(column_name) AS non_null_count,
    CAST(100.0 * (COUNT(*) - COUNT(column_name)) / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS null_pct
FROM schema.table_name;
```

---

## PostgreSQL / Azure Database for PostgreSQL

### List all tables
```sql
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename;
```

### Column details
```sql
SELECT 
    c.column_name,
    c.data_type,
    c.character_maximum_length,
    c.is_nullable,
    c.column_default,
    pgd.description
FROM information_schema.columns c
LEFT JOIN pg_catalog.pg_statio_all_tables st 
    ON c.table_schema = st.schemaname AND c.table_name = st.relname
LEFT JOIN pg_catalog.pg_description pgd 
    ON pgd.objoid = st.relid AND pgd.objsubid = c.ordinal_position
WHERE c.table_schema = $1 AND c.table_name = $2
ORDER BY c.ordinal_position;
```

### Primary keys
```sql
SELECT a.attname
FROM pg_index i
JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
WHERE i.indrelid = $1::regclass AND i.indisprimary;
```

### Foreign keys
```sql
SELECT
    tc.constraint_name,
    kcu.column_name AS from_column,
    ccu.table_schema AS to_schema,
    ccu.table_name AS to_table,
    ccu.column_name AS to_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu 
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = $1 AND tc.table_name = $2;
```

### Row counts (fast approximate)
```sql
SELECT schemaname, relname, n_live_tup AS approximate_row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```

### Distinct values and top values
```sql
-- Distinct count
SELECT COUNT(DISTINCT column_name) FROM schema.table;

-- Top values
SELECT column_name, COUNT(*) as freq
FROM schema.table
GROUP BY column_name
ORDER BY freq DESC
LIMIT 10;
```

---

## MySQL / Azure Database for MySQL

### List all tables
```sql
SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_ROWS, DATA_LENGTH
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
ORDER BY TABLE_SCHEMA, TABLE_NAME;
```

### Column details
```sql
SELECT 
    COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
    IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @schema AND TABLE_NAME = @table
ORDER BY ORDINAL_POSITION;
```

### Foreign keys
```sql
SELECT 
    CONSTRAINT_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_SCHEMA,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = @schema 
    AND TABLE_NAME = @table
    AND REFERENCED_TABLE_NAME IS NOT NULL;
```

---

## SQLite

### List all tables
```sql
SELECT name, type FROM sqlite_master 
WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'
ORDER BY name;
```

### Column details
```sql
PRAGMA table_info('table_name');
```

### Foreign keys
```sql
PRAGMA foreign_key_list('table_name');
```

### Indexes
```sql
PRAGMA index_list('table_name');
```

---

## Universal Profiling Patterns

These work across most SQL databases with minor syntax adjustments:

### Sample rows
```sql
SELECT * FROM schema.table LIMIT 5;          -- PostgreSQL, MySQL, SQLite
SELECT TOP 5 * FROM schema.table;            -- SQL Server
```

### Basic column profile
```sql
SELECT
    COUNT(*) AS total_rows,
    COUNT(col) AS non_null,
    COUNT(DISTINCT col) AS distinct_values,
    MIN(col) AS min_value,
    MAX(col) AS max_value
FROM schema.table;
```
