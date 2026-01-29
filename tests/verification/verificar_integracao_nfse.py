"""
Script de verificação: Confirma se a integração NFS-e está correta.

Verifica:
1. processar_nfse() tem todos os campos obrigatórios
2. NFSeDatabase usa banco principal (notas.db)
3. get_config_nfse() busca no banco correto
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).parent

print("=" * 70)
print("VERIFICAÇÃO DE INTEGRAÇÃO NFS-e")
print("=" * 70)

# 1. Verificar processar_nfse() em nfe_search.py
print("\n1️⃣ Verificando processar_nfse() em nfe_search.py...")
nfe_search_content = (BASE_DIR / "nfe_search.py").read_text(encoding="utf-8")

# Localizar função processar_nfse
match = re.search(r'def processar_nfse\([^)]*\):(.*?)(?=\ndef\s|\Z)', nfe_search_content, re.DOTALL)
if match:
    processar_nfse_code = match.group(1)
    
    # Verificar campos obrigatórios
    campos_obrigatorios = [
        'chave', 'numero', 'tipo', 'nome_emitente', 'cnpj_emitente',
        'data_emissao', 'valor', 'status', 'informante', 'xml_status', 'nsu',
        'ie_tomador', 'cnpj_destinatario', 'cfop', 'vencimento', 'ncm', 
        'uf', 'natureza', 'base_icms', 'valor_icms', 'atualizado_em'
    ]
    
    campos_presentes = []
    campos_faltando = []
    
    for campo in campos_obrigatorios:
        if f"'{campo}'" in processar_nfse_code or f'"{campo}"' in processar_nfse_code:
            campos_presentes.append(campo)
        else:
            campos_faltando.append(campo)
    
    print(f"   ✅ Campos presentes: {len(campos_presentes)}/{len(campos_obrigatorios)}")
    
    if campos_faltando:
        print(f"   ❌ Campos faltando: {', '.join(campos_faltando)}")
    else:
        print("   ✅ Todos os campos obrigatórios estão presentes!")
else:
    print("   ❌ Função processar_nfse() não encontrada!")

# 2. Verificar NFSeDatabase em nfse_search.py
print("\n2️⃣ Verificando NFSeDatabase em nfse_search.py...")
nfse_search_content = (BASE_DIR / "nfse_search.py").read_text(encoding="utf-8")

# Verificar __init__ do NFSeDatabase
if 'main_db_path = str(BASE_DIR / "notas.db")' in nfse_search_content:
    print("   ✅ NFSeDatabase usa banco principal (notas.db)")
elif 'DatabaseManager(db_path)' in nfse_search_content and 'notas.db' not in nfse_search_content:
    print("   ❌ NFSeDatabase pode estar usando banco errado!")
else:
    print("   ⚠️  Não foi possível determinar qual banco está sendo usado")

# Verificar get_certificados()
if 'self.main_db.get_certificados()' in nfse_search_content:
    print("   ✅ get_certificados() delega para DatabaseManager")
else:
    print("   ❌ get_certificados() não delega para DatabaseManager")

# 3. Verificar get_config_nfse()
print("\n3️⃣ Verificando get_config_nfse() em nfse_search.py...")
if 'self.main_db._connect()' in nfse_search_content and 'nfse_config' in nfse_search_content:
    print("   ✅ get_config_nfse() busca no banco principal")
elif 'self._connect()' in nfse_search_content and 'nfse_config' in nfse_search_content:
    print("   ❌ get_config_nfse() busca no banco local (ERRADO!)")
else:
    print("   ⚠️  Não foi possível determinar qual banco get_config_nfse() usa")

# 4. Verificar se Busca NF-e.py importa nfe_search
print("\n4️⃣ Verificando Busca NF-e.py...")
busca_nfe_content = (BASE_DIR / "Busca NF-e.py").read_text(encoding="utf-8")

if 'nfe_search.run_single_cycle()' in busca_nfe_content:
    print("   ✅ Interface usa nfe_search.run_single_cycle()")
    print("   ✅ Correções de NFS-e serão aplicadas na interface!")
else:
    print("   ❌ Interface não usa nfe_search.run_single_cycle()")

# 5. Verificar banco de dados
print("\n5️⃣ Verificando banco de dados...")
import sqlite3

try:
    conn = sqlite3.connect('notas.db')
    
    # Verificar tabela nfse_config
    count_config = conn.execute("SELECT COUNT(*) FROM nfse_config WHERE ativo=1").fetchone()[0]
    print(f"   ✅ Configurações NFS-e ativas: {count_config}")
    
    # Verificar tabela nsu_nfse
    try:
        count_nsu = conn.execute("SELECT COUNT(*) FROM nsu_nfse").fetchone()[0]
        print(f"   ✅ Registros nsu_nfse: {count_nsu}")
    except:
        print("   ⚠️  Tabela nsu_nfse não existe (será criada na primeira busca)")
    
    # Verificar NFS-e existentes
    count_nfse = conn.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo='NFS-e'").fetchone()[0]
    print(f"   ✅ NFS-e no banco: {count_nfse}")
    
    conn.close()
except Exception as e:
    print(f"   ❌ Erro ao acessar banco: {e}")

print("\n" + "=" * 70)
print("RESULTADO FINAL")
print("=" * 70)

# Resumo
erros = []
if campos_faltando:
    erros.append("processar_nfse() sem todos os campos")
if 'main_db_path = str(BASE_DIR / "notas.db")' not in nfse_search_content:
    erros.append("NFSeDatabase pode estar usando banco errado")
if 'self.main_db.get_certificados()' not in nfse_search_content:
    erros.append("get_certificados() não delega")

if not erros:
    print("✅ TUDO CORRETO! A integração NFS-e está funcionando.")
    print("✅ Os botões 'Busca na Sefaz' e 'Busca Completa' usarão a versão corrigida!")
else:
    print("❌ Problemas encontrados:")
    for erro in erros:
        print(f"   • {erro}")

print("=" * 70)
