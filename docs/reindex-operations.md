# Nightly Re-index Operations (DE-07 / DE-10)

## Manual Trigger
```bash
cd /path/to/icsa-ai-service && python scripts/cron/reindex.py
```

## Check Last Run
```bash
tail -5 logs/reindex.log
```
Each line format: `YYYY-MM-DD HH:MM:SS | extract: 0 | embed: 0` (0 = success).

## Change Cron Schedule (Linux/Mac)
```bash
crontab -e
# 2 AM daily — change the leading "2" to the desired hour:
0 2 * * * cd /path/to/icsa-ai-service && python scripts/cron/reindex.py
crontab -l   # verify entry exists
```

## Schedule on Windows
Task Scheduler → Create Basic Task → Daily, 2:00 AM →
Action: Start a program → `python` → arguments `scripts/cron/reindex.py` →
Start in: repo folder path.

## If Reindex Fails
1. Check `logs/reindex.log` for a non-zero exit code.
2. Verify PSS DB is reachable: `python scripts/db_connection.py`
3. Verify pgvector container is running: `docker ps`
4. Re-run manually after fixing the issue.

Re-index is an **upsert** (ON CONFLICT DO UPDATE): running twice never
duplicates rows — pgvector COUNT(*) stays equal or grows.
