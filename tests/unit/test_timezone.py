"""Testa timezone do sistema"""
from datetime import datetime

now_local = datetime.now().astimezone()
print(f"Hora local: {now_local}")
print(f"Timezone: {now_local.tzinfo}")
print(f"UTC offset: {now_local.utcoffset()}")
print(f"Formato ISO: {now_local.isoformat()}")

# Formato para NF-e
dh_evento = now_local.strftime('%Y-%m-%dT%H:%M:%S%z')
dh_evento = dh_evento[:-2] + ':' + dh_evento[-2:]
print(f"dhEvento: {dh_evento}")

# Forçar timezone -03:00 (Brasília)
from datetime import timezone, timedelta
brasilia_tz = timezone(timedelta(hours=-3))
now_brasilia = datetime.now(brasilia_tz)
dh_brasilia = now_brasilia.strftime('%Y-%m-%dT%H:%M:%S%z')
dh_brasilia = dh_brasilia[:-2] + ':' + dh_brasilia[-2:]
print(f"dhEvento Brasília: {dh_brasilia}")
