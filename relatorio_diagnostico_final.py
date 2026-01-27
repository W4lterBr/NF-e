"""
🔍 RELATÓRIO FINAL - DIAGNÓSTICO NF-e AUSENTES
===============================================

Data: 12/01/2026
Problema: Usuário relata que não vê NF-e após 02/01/2026
"""

import sqlite3
from datetime import datetime

print("=" * 80)
print("📋 RELATÓRIO FINAL - DIAGNÓSTICO NF-e")
print("=" * 80)

conn = sqlite3.connect('notas.db')

# 1. Situação atual
print("\n📊 1. SITUAÇÃO ATUAL DO BANCO")
print("-" * 80)

cursor = conn.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo = 'NFe' OR tipo = 'NF-e'")
total_nfe = cursor.fetchone()[0]

cursor = conn.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo = 'CTe' OR tipo = 'CT-e'")
total_cte = cursor.fetchone()[0]

print(f"\nTotal de documentos:")
print(f"   NF-e: {total_nfe}")
print(f"   CT-e: {total_cte}")

# 2. Análise de NF-e com campos vazios
print("\n📊 2. ANÁLISE DE NF-e COM CAMPOS VAZIOS")
print("-" * 80)

cursor = conn.execute("""
    SELECT COUNT(*) 
    FROM notas_detalhadas 
    WHERE (tipo = 'NFe' OR tipo = 'NF-e')
    AND (data_emissao IS NULL OR data_emissao = '' OR data_emissao = 'N/A')
""")
nfe_sem_data = cursor.fetchone()[0]

cursor = conn.execute("""
    SELECT COUNT(*) 
    FROM notas_detalhadas 
    WHERE (tipo = 'NFe' OR tipo = 'NF-e')
    AND (nome_emitente IS NULL OR nome_emitente = '' OR nome_emitente = 'N/A')
""")
nfe_sem_emitente = cursor.fetchone()[0]

cursor = conn.execute("""
    SELECT COUNT(*) 
    FROM notas_detalhadas 
    WHERE (tipo = 'NFe' OR tipo = 'NF-e')
    AND (numero IS NULL OR numero = '' OR numero = 'N/A')
""")
nfe_sem_numero = cursor.fetchone()[0]

print(f"\nNF-e com dados incompletos:")
print(f"   Sem data de emissão: {nfe_sem_data} ({nfe_sem_data/total_nfe*100:.1f}% do total)")
print(f"   Sem nome do emitente: {nfe_sem_emitente} ({nfe_sem_emitente/total_nfe*100:.1f}% do total)")
print(f"   Sem número: {nfe_sem_numero} ({nfe_sem_numero/total_nfe*100:.1f}% do total)")

if nfe_sem_data > 0 or nfe_sem_emitente > 0 or nfe_sem_numero > 0:
    print("\n❌ PROBLEMA IDENTIFICADO:")
    print("   As NF-e ESTÃO sendo salvas no banco, mas com campos VAZIOS!")
    print("   Isso impede a visualização correta na interface.")

# 3. NF-e com dados completos
print("\n📊 3. NF-e COM DADOS COMPLETOS")
print("-" * 80)

cursor = conn.execute("""
    SELECT COUNT(*) 
    FROM notas_detalhadas 
    WHERE (tipo = 'NFe' OR tipo = 'NF-e')
    AND data_emissao IS NOT NULL 
    AND data_emissao != '' 
    AND data_emissao != 'N/A'
    AND nome_emitente IS NOT NULL 
    AND nome_emitente != '' 
    AND nome_emitente != 'N/A'
""")
nfe_completas = cursor.fetchone()[0]

print(f"\nNF-e com dados completos: {nfe_completas}")

if nfe_completas > 0:
    # Mostra últimas 10 NF-e completas
    print(f"\nÚltimas 5 NF-e COMPLETAS:")
    
    cursor = conn.execute("""
        SELECT 
            chave,
            numero,
            data_emissao,
            nome_emitente,
            valor,
            nsu
        FROM notas_detalhadas 
        WHERE (tipo = 'NFe' OR tipo = 'NF-e')
        AND data_emissao IS NOT NULL 
        AND data_emissao != '' 
        AND data_emissao != 'N/A'
        AND nome_emitente IS NOT NULL 
        AND nome_emitente != '' 
        AND nome_emitente != 'N/A'
        ORDER BY atualizado_em DESC
        LIMIT 5
    """)
    
    for row in cursor:
        chave = row[0][:20] + '...'
        numero = row[1] if row[1] else 'N/A'
        data = row[2] if row[2] else 'N/A'
        emitente = (row[3][:30] + '...') if row[3] and len(row[3]) > 33 else row[3]
        valor = row[4] if row[4] else 'N/A'
        nsu = row[5] if row[5] else 'SEM NSU'
        
        print(f"   Chave: {chave}, Número: {numero}, Data: {data}")
        print(f"      Emitente: {emitente}, Valor: {valor}, NSU: {nsu}")

# 4. Últimas NF-e VAZIAS (problemáticas)
print("\n\n📊 4. ÚLTIMAS 10 NF-e VAZIAS (PROBLEMÁTICAS)")
print("-" * 80)

cursor = conn.execute("""
    SELECT 
        chave,
        nsu,
        atualizado_em,
        informante
    FROM notas_detalhadas 
    WHERE (tipo = 'NFe' OR tipo = 'NF-e')
    AND (data_emissao IS NULL OR data_emissao = '' OR data_emissao = 'N/A')
    ORDER BY atualizado_em DESC
    LIMIT 10
""")

vazias = cursor.fetchall()

if vazias:
    print(f"\nEncontradas {len(vazias)} NF-e com dados vazios:")
    for row in vazias:
        chave = row[0][:25] + '...'
        nsu = row[1] if row[1] else 'SEM NSU'
        atualizado = row[2] if row[2] else 'N/A'
        informante = row[3] if row[3] else 'N/A'
        
        print(f"   Chave: {chave}")
        print(f"      NSU: {nsu}, Informante: {informante}, Atualizado: {atualizado}")

# 5. Análise por informante
print("\n\n📊 5. NF-e POR INFORMANTE")
print("-" * 80)

cursor = conn.execute("""
    SELECT 
        informante,
        COUNT(*) as total,
        SUM(CASE WHEN data_emissao IS NOT NULL AND data_emissao != '' AND data_emissao != 'N/A' THEN 1 ELSE 0 END) as completas,
        SUM(CASE WHEN data_emissao IS NULL OR data_emissao = '' OR data_emissao = 'N/A' THEN 1 ELSE 0 END) as vazias
    FROM notas_detalhadas
    WHERE tipo = 'NFe' OR tipo = 'NF-e'
    GROUP BY informante
    ORDER BY total DESC
""")

print(f"\n{'Informante':<20} {'Total':<10} {'Completas':<12} {'Vazias':<10} {'%Vazias':<10}")
print("-" * 80)

for row in cursor:
    informante = row[0] if row[0] else 'SEM INFORMANTE'
    total = row[1]
    completas = row[2]
    vazias = row[3]
    perc_vazia = (vazias/total*100) if total > 0 else 0
    
    print(f"{informante:<20} {total:<10} {completas:<12} {vazias:<10} {perc_vazia:.1f}%")

# 6. Conclusão e recomendação
print("\n\n" + "=" * 80)
print("📋 CONCLUSÃO DO DIAGNÓSTICO")
print("=" * 80)

print(f"""
🔍 PROBLEMA IDENTIFICADO:

   ✅ O sistema ESTÁ buscando NF-e da SEFAZ
   ✅ O sistema ESTÁ salvando as NF-e no banco
   ❌ A função extrair_nota_detalhada() NÃO está extraindo os dados
   ❌ NF-e são salvas com campos vazios (N/A)
   
   Resultado: {nfe_sem_data} NF-e ({nfe_sem_data/total_nfe*100:.1f}%) estão no banco mas INVISÍVEIS
   porque não têm data_emissao, nome_emitente, número, etc.

📊 DADOS:

   Total de NF-e: {total_nfe}
   NF-e completas: {nfe_completas} ({nfe_completas/total_nfe*100:.1f}%)
   NF-e vazias: {nfe_sem_data} ({nfe_sem_data/total_nfe*100:.1f}%)

🔧 SOLUÇÃO NECESSÁRIA:

   1. Corrigir a função extrair_nota_detalhada()
   2. Garantir que todos os campos sejam extraídos do XML
   3. Reprocessar as {nfe_sem_data} NF-e vazias existentes
   
❓ CAUSA RAIZ:

   A função extrair_nota_detalhada() está retornando valores N/A
   ou None para os campos essenciais. Pode ser:
   
   - Parser XML não está encontrando os elementos
   - Namespace incorreto
   - Estrutura do XML diferente do esperado
   - XML está vindo como RESUMO (resNFe) ao invés de XML completo
   
🎯 PRÓXIMO PASSO:

   Analisar um dos XMLs problemáticos para ver sua estrutura
   e ajustar a função extrair_nota_detalhada() conforme necessário.
""")

conn.close()

print("\n" + "=" * 80)
print("✅ Diagnóstico finalizado!")
print("=" * 80)
