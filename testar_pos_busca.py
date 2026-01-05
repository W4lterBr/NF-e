#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste da função de atualização de status pós-busca
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.database import DatabaseManager
from datetime import datetime, timedelta

def testar_separacao_documentos():
    """Testa a separação de NF-es e CT-es"""
    
    print("🧪 Testando separação de documentos para atualização pós-busca\n")
    print("="*80)
    
    # Inicializa database
    db_path = os.path.join(os.path.dirname(__file__), "notas.db")
    db = DatabaseManager(db_path)
    
    # Carrega documentos
    notes = db.load_notes(limit=5000)
    
    # Obtém apenas documentos dos ÚLTIMOS 7 DIAS (como faz a função)
    data_limite = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    chaves_nfe = []
    chaves_cte = []
    
    print(f"\n📅 Data limite: {data_limite}")
    print(f"📋 Total de documentos no banco: {len(notes)}\n")
    
    for nota in notes:
        status = (nota.get('status') or '').lower()
        chave = nota.get('chave')
        data_emissao = (nota.get('data_emissao') or '')[:10]
        tipo = (nota.get('tipo') or '').upper()
        
        # Consulta apenas documentos RECENTES e AUTORIZADOS
        if (chave and len(chave) == 44 and 
            'autoriza' in status and 
            data_emissao >= data_limite):
            
            # Separa por tipo
            if tipo == 'CTE':
                chaves_cte.append({
                    'chave': chave,
                    'data': data_emissao,
                    'status': status,
                    'numero': nota.get('numero')
                })
            else:
                chaves_nfe.append({
                    'chave': chave,
                    'data': data_emissao,
                    'status': status,
                    'numero': nota.get('numero')
                })
    
    total_docs = len(chaves_nfe) + len(chaves_cte)
    
    print(f"📊 Resultado da Separação:")
    print(f"   ✅ Total de documentos recentes autorizados: {total_docs}")
    print(f"   📄 NF-es: {len(chaves_nfe)}")
    print(f"   🚛 CT-es: {len(chaves_cte)}")
    
    # Mostra exemplos de NF-es
    if chaves_nfe:
        print(f"\n📄 Exemplos de NF-es ({min(5, len(chaves_nfe))} de {len(chaves_nfe)}):")
        for i, doc in enumerate(chaves_nfe[:5], 1):
            print(f"   {i}. Nº {doc['numero']} - {doc['data']} - {doc['chave'][:44]}")
    
    # Mostra exemplos de CT-es
    if chaves_cte:
        print(f"\n🚛 Exemplos de CT-es ({min(5, len(chaves_cte))} de {len(chaves_cte)}):")
        for i, doc in enumerate(chaves_cte[:5], 1):
            print(f"   {i}. Nº {doc['numero']} - {doc['data']} - {doc['chave'][:44]}")
    
    if total_docs == 0:
        print("\n⚠️ Nenhum documento recente para atualizar")
        print("   Isso é normal se:")
        print("   - Não há documentos emitidos nos últimos 7 dias")
        print("   - Todos os documentos recentes já foram cancelados")
    else:
        print(f"\n✅ A função irá consultar eventos de {total_docs} documentos!")
        print(f"   Sequência: Primeiro NF-es ({len(chaves_nfe)}), depois CT-es ({len(chaves_cte)})")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    testar_separacao_documentos()
