# -*- coding: utf-8 -*-
"""
Configura certificado para teste de NFS-e
"""
import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))
from nfse_search import NFSeDatabase, logger

# Inicializa banco
db = NFSeDatabase()

# Configura MATPARCG (Campo Grande/MS)
cnpj = "33251845000109"
cod_municipio = "5002704"  # Campo Grande/MS
inscricao = "000000000"  # Placeholder - usuário deve atualizar

print(f"\n{'='*70}")
print("CONFIGURANDO NFS-e PARA TESTE")
print(f"{'='*70}")
print(f"CNPJ: {cnpj}")
print(f"Município: {cod_municipio} (Campo Grande/MS)")
print(f"Provedor: AMBIENTE_NACIONAL (consulta própria)")
print(f"{'='*70}\n")

try:
    # Adiciona nova configuração para Ambiente Nacional
    db.adicionar_config_nfse(
        cnpj=cnpj,
        provedor="AMBIENTE_NACIONAL",
        cod_municipio=cod_municipio,
        inscricao_municipal=inscricao,
        url=None
    )
    
    print("✅ Configuração NFS-e adicionada com sucesso!")
    print(f"\nCertificado {cnpj} configurado para:")
    print(f"  - Município: {cod_municipio}")
    print(f"  - Provedor: AMBIENTE_NACIONAL")
    print(f"  - Método: Consulta própria via certificado digital\n")
    
    # Verifica configuração
    configs = db.get_config_nfse(cnpj)
    print(f"Verificação: {len(configs)} configuração(ões) encontrada(s)")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
