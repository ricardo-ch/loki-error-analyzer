# Loki Query Customization Examples

This document shows how to use the new `--loki-query` and `--loki-query-params` arguments to run custom Loki queries.

## Basic Usage

### Using Python script directly:

```bash
python3 loki_error_analyzer.py \
  --loki-query "orgId=loki-tutti-prod" \
  --loki-query-params '{"namespace":"live-tutti-services","detected_level":"info"}' \
  --env dev \
  --limit 1000
```

### Using the shell script:

```bash
./run_analyzer.sh \
  --loki-query "orgId=loki-tutti-prod" \
  --loki-query-params '{"namespace":"live-tutti-services","detected_level":"info"}' \
  --env dev \
  --limit 1000
```

## What This Does

The command above will:

1. **Set orgId**: `loki-tutti-prod` (overrides the default orgId from config)
2. **Generate LogQL query**: `{namespace="live-tutti-services"} | detected_level!="info"`
3. **Query Loki**: Fetch logs where:
   - namespace = "live-tutti-services"
   - detected_level is NOT "info" (i.e., error, warn, debug, etc.)

## Query Parameters

The `--loki-query-params` argument expects a JSON string with:

- `namespace`: The Kubernetes namespace to filter by
- `detected_level`: The log level to exclude (logs with this level will be filtered out)

## Generated LogQL Query

The system automatically generates this LogQL query:
```
{namespace="live-tutti-services"} | detected_level!="info"
```

This query will return all logs from the `live-tutti-services` namespace where the `detected_level` field is not equal to "info".

## Other Examples

### Query for errors and warnings only:
```bash
python3 loki_error_analyzer.py \
  --loki-query "orgId=loki-tutti-prod" \
  --loki-query-params '{"namespace":"live-tutti-services","detected_level":"debug"}' \
  --env dev
```

### Query with custom time range:
```bash
python3 loki_error_analyzer.py \
  --loki-query "orgId=loki-tutti-prod" \
  --loki-query-params '{"namespace":"live-tutti-services","detected_level":"info"}' \
  --start-time "2024-01-15T19:00:00Z" \
  --end-time "2024-01-15T22:00:00Z" \
  --env dev
```

## Notes

- The `--loki-query` argument is required when using custom queries
- The `--loki-query-params` argument is required and must contain both `namespace` and `detected_level`
- The orgId from `--loki-query` will override the default orgId from the configuration
- All other arguments (--env, --limit, --start-time, etc.) work as before
