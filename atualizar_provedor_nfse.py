"""
Script para atualizar provedor de NFS-e para Nuvem Fiscal
"""

import sys
import io
from pathlib import Path

# Força UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from nfse_search import NFSeDatabase

db = NFSeDatabase()

# Atualiza certificado 33251845000109 para usar Nuvem Fiscal
cnpj = "33251845000109"
cod_municipio = "5002704"  # Campo Grande/MS
inscricao = ""  # Inscrição municipal (pode ser vazia para testes)

print("\n📝 Atualizando configuração de NFS-e...")
print(f"   CNPJ: {cnpj}")
print(f"   Município: Campo Grande/MS ({cod_municipio})")
print(f"   Provedor: NUVEMFISCAL (API REST)")

db.adicionar_config_nfse(
    cnpj=cnpj,
    provedor="NUVEMFISCAL",
    cod_municipio=cod_municipio,
    inscricao_municipal=inscricao,
    url=None
)

print("✅ Configuração atualizada com sucesso!")
print("\n🚀 Agora execute: python buscar_nfse_auto.py\n")
