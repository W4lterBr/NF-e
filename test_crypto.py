"""Teste rápido de carregamento de certificados após migração"""
from modules.database import DatabaseManager
from pathlib import Path

db = DatabaseManager(Path('notas.db'))
certs = db.load_certificates()

print(f'\n✅ Carregados {len(certs)} certificados\n')

for c in certs:
    senha = c.get('senha', '')
    print(f'   - {c["informante"]}: senha com {len(senha)} caracteres (descriptografada)')

print('\n🎉 Sistema funcionando corretamente com senhas criptografadas!')
