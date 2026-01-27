"""
🔧 CORRIGE NSU FALTANTES
Adiciona registros NSU para certificados que não têm
"""

import sqlite3
import sys
from pathlib import Path

# Adiciona o diretório base ao path
BASE_DIR = Path(__file__).parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from modules.crypto_portable import PortableCryptoManager

DB_PATH = Path(__file__).parent / "notas_test.db"
crypto = PortableCryptoManager()

print("=" * 80)
print("🔧 CORRIGINDO NSU FALTANTES")
print("=" * 80)

with sqlite3.connect(DB_PATH) as conn:
    # 1. Busca todos os certificados
    certs = conn.execute("SELECT cnpj_cpf, informante FROM certificados").fetchall()
    
    # 2. Busca NSUs existentes
    nsus_existentes = {crypto.decrypt(inf) for inf, _ in conn.execute("SELECT informante, ult_nsu FROM nsu").fetchall()}
    
    print(f"\n📋 Certificados cadastrados: {len(certs)}")
    print(f"📊 NSUs existentes: {len(nsus_existentes)}")
    
    # 3. Identifica certificados sem NSU
    faltantes = []
    for cnpj, inf_enc in certs:
        inf = crypto.decrypt(inf_enc)
        if inf not in nsus_existentes:
            faltantes.append((cnpj, inf_enc))
    
    if len(faltantes) == 0:
        print("\n✅ Todos os certificados já têm NSU registrado!")
    else:
        print(f"\n⚠️ {len(faltantes)} certificados sem NSU:")
        for cnpj, _ in faltantes:
            print(f"   • {cnpj}")
        
        print("\n🔧 Adicionando NSU inicial (000000000000000) para certificados faltantes...")
        
        for cnpj, inf_enc in faltantes:
            conn.execute(
                "INSERT OR REPLACE INTO nsu (informante, ult_nsu) VALUES (?, ?)",
                (inf_enc, '000000000000000')
            )
            print(f"   ✅ NSU adicionado para {cnpj}")
        
        conn.commit()
        
        print("\n✅ Correção concluída!")
        print("\n📝 Próximo passo: Execute uma busca para que esses certificados atualizem seus NSUs")

print("=" * 80)
