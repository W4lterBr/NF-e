from pathlib import Path
import sys

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

from nfe_search import DatabaseManager  # noqa

mgr = DatabaseManager(BASE / 'notas.db')
rows = mgr.get_certificados()
print('CERTS', len(rows))
for r in rows:
    print('ROW', r)
