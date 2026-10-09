"""retention.py - delete expired option/futures files in db_migrate_json/Archived_All.
Options: folders older than 21 days after expiry. Futures: contract files not written for 92 days.
Run after market close (called from standalone_archive_script.bat):
    tg-flask-venv\\Scripts\\python db_migrate_json\\retention.py            # delete
    tg-flask-venv\\Scripts\\python db_migrate_json\\retention.py --dry-run  # only list
Every action is logged to opt_fut_entry_logger.log."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import jsonl_store as S

dry = '--dry-run' in sys.argv
for ul in list(S.EXPIRY_KEY):
    S.roll(ul)                     # also move folders whose expiry passed, even on a day with no writes
paths = S.retention(dry_run=dry)
print(('Would delete' if dry else 'Deleted') + ' %d item(s)' % len(paths))
for p in paths:
    print('  ' + os.path.relpath(p, S.ROOT))
