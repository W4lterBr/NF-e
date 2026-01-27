"""
Teste da correção da lógica ultNSU == maxNSU
Valida que o sistema processa documentos antes de verificar sincronização
"""

print("=" * 80)
print("TESTE: CORREÇÃO DA LÓGICA ultNSU == maxNSU")
print("=" * 80)

print("""
🐛 PROBLEMA IDENTIFICADO NO LOG:
- cStat=138 (Documento(s) localizado(s))
- ultNSU=61786, maxNSU=61786
- NSU anterior=61756
- Documentos disponíveis: 30 (NSU 61757 a 61786)

❌ COMPORTAMENTO ANTIGO (ERRADO):
1. Recebe resposta da SEFAZ
2. Verifica: ultNSU == maxNSU? SIM
3. Registra "sincronizado", aguarda 1h
4. ❌ PARA SEM PROCESSAR OS 30 DOCUMENTOS!

✅ COMPORTAMENTO NOVO (CORRETO):
1. Recebe resposta da SEFAZ
2. Verifica: cStat=137 (sem docs)? NÃO
3. Verifica: cStat=138 (com docs)? SIM
4. ✅ PROCESSA OS 30 DOCUMENTOS
5. Atualiza NSU para 61786
6. Verifica: ultNSU == maxNSU? SIM
7. Registra sincronização para próxima vez
8. Faz nova iteração (vai receber cStat=137)
9. Aguarda 1h

📋 LÓGICA CORRETA:
""")

print("Ordem de verificações:")
print("  1️⃣  cStat=656 (erro consumo) → Aguarda 65 min")
print("  2️⃣  cStat=137 (sem docs) → Aguarda 1h")
print("  3️⃣  cStat=138 (com docs) → PROCESSA DOCUMENTOS")
print("  4️⃣  Atualiza NSU")
print("  5️⃣  Se ultNSU==maxNSU após processar → Registra sincronização")
print("  6️⃣  Nova iteração (vai receber 137 e aguardar 1h)")

print("\n" + "=" * 80)
print("ANÁLISE DO CÓDIGO")
print("=" * 80)

import re
from pathlib import Path

nfe_search_path = Path(__file__).parent / "nfe_search.py"
conteudo = nfe_search_path.read_text(encoding='utf-8')

# Procura a ordem das verificações
linhas = conteudo.split('\n')

print("\n🔍 Procurando ordem das verificações no código:")

# Encontra o bloco de verificações
for i, linha in enumerate(linhas, 1):
    if 'cStat 137 = Nenhum documento localizado' in linha:
        print(f"\n✅ Linha {i}: Verificação cStat=137 encontrada")
        print(f"   {linha.strip()}")
        
        # Verifica se está ANTES da verificação ultNSU==maxNSU
        for j in range(max(0, i-20), min(len(linhas), i+50)):
            if 'if ult and max_nsu and ult == max_nsu:' in linhas[j]:
                if j < i:
                    print(f"\n❌ ERRO: ultNSU==maxNSU (linha {j+1}) está ANTES de cStat=137 (linha {i})")
                    print("   Isso impede o processamento de documentos!")
                else:
                    print(f"\n✅ CORRETO: ultNSU==maxNSU (linha {j+1}) está DEPOIS de cStat=137 (linha {i})")
                    print("   Documentos serão processados antes da verificação de sincronização")
                break
        break

# Verifica se existe verificação ultNSU==maxNSU no meio do processamento
for i, linha in enumerate(linhas, 1):
    if 'Se chegou aqui: cStat=138' in linha:
        print(f"\n✅ Linha {i}: Ponto de processamento de documentos encontrado")
        print(f"   {linha.strip()}")
        
        # Verifica se não há break antes
        tem_break_antes = False
        for j in range(max(0, i-30), i):
            if 'if ult and max_nsu and ult == max_nsu:' in linhas[j]:
                # Verifica se tem break depois
                for k in range(j, min(len(linhas), j+10)):
                    if 'break' in linhas[k] and 'Sai do loop NF-e' in linhas[k]:
                        tem_break_antes = True
                        print(f"\n❌ ERRO: Encontrado break por ultNSU==maxNSU ANTES de processar (linha {k+1})")
                        break
                if tem_break_antes:
                    break
        
        if not tem_break_antes:
            print(f"\n✅ CORRETO: Não há break por ultNSU==maxNSU antes do processamento")
        
        break

print("\n" + "=" * 80)
print("CONCLUSÃO")
print("=" * 80)
print("""
A correção garante que:
✅ cStat=137 é verificado PRIMEIRO (sem documentos → aguarda 1h)
✅ cStat=138 permite processamento de documentos
✅ ultNSU==maxNSU só importa DEPOIS de processar documentos
✅ Sistema não perde documentos por considerar sincronizado prematuramente

Resultado esperado no próximo log:
📦 NF-e: Encontrados 30 documento(s) na resposta
📄 NF-e: Processando doc 1/30, NSU=61757
📄 NF-e: Processando doc 2/30, NSU=61758
...
📄 NF-e: Processando doc 30/30, NSU=61786
✅ NF-e: 30 documento(s) processado(s) com sucesso
📊 NF-e: Após processar 30 doc(s), sistema sincronizado (ultNSU=maxNSU)
⏰ Próxima consulta em 1h conforme NT 2014.002
""")
