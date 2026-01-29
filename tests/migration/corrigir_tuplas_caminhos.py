"""
🔧 CORREÇÃO CRÍTICA - Limpa tuplas do campo caminho_arquivo
Este script corrige registros em xmls_baixados onde o caminho foi salvo como representação de tupla
em vez de string, causando falha na auto-detecção de xml_status.

Problema: caminho_arquivo = "('C:/path/file.xml', 'C:/path/file.pdf')" em vez de "C:/path/file.xml"
Solução: Extrai primeiro elemento da tupla e valida se o arquivo existe
"""

import sqlite3
from pathlib import Path
import re

def main():
    print("=" * 80)
    print("🔧 CORREÇÃO CRÍTICA - Limpeza de tuplas em caminho_arquivo")
    print("=" * 80)
    
    conn = sqlite3.connect('notas.db')
    cursor = conn.cursor()
    
    # 1. Identifica registros com tuplas
    print("\n📊 1. IDENTIFICANDO REGISTROS COM TUPLAS")
    print("-" * 80)
    
    cursor.execute("""
        SELECT chave, caminho_arquivo
        FROM xmls_baixados
        WHERE caminho_arquivo LIKE "(%)"
           OR caminho_arquivo LIKE "'%'"
    """)
    
    registros_tupla = cursor.fetchall()
    print(f"   Registros com formato de tupla: {len(registros_tupla)}")
    
    if not registros_tupla:
        print("   ✅ Nenhum registro com tupla encontrado!")
        conn.close()
        return
    
    # 2. Corrige cada registro
    print("\n🔧 2. CORRIGINDO REGISTROS")
    print("-" * 80)
    
    corrigidos = 0
    removidos = 0
    invalidos = 0
    
    for chave, caminho_tupla in registros_tupla:
        try:
            # Extrai primeiro elemento da tupla usando regex
            # Padrão: ('caminho1', 'caminho2') ou ('caminho1', None)
            match = re.search(r"\('([^']+)'", caminho_tupla)
            
            if match:
                caminho_limpo = match.group(1)
                
                # Verifica se arquivo existe
                if Path(caminho_limpo).exists():
                    # Atualiza com caminho limpo
                    cursor.execute(
                        "UPDATE xmls_baixados SET caminho_arquivo = ? WHERE chave = ?",
                        (caminho_limpo, chave)
                    )
                    corrigidos += 1
                    if corrigidos <= 5:  # Mostra primeiros 5
                        print(f"   ✅ {chave[:25]}... → {caminho_limpo[:50]}...")
                else:
                    # Arquivo não existe, remove o caminho
                    cursor.execute(
                        "UPDATE xmls_baixados SET caminho_arquivo = NULL WHERE chave = ?",
                        (chave,)
                    )
                    removidos += 1
                    if removidos <= 5:
                        print(f"   ⚠️ {chave[:25]}... → REMOVIDO (arquivo não existe)")
            else:
                # Não conseguiu extrair caminho, invalida
                cursor.execute(
                    "UPDATE xmls_baixados SET caminho_arquivo = NULL WHERE chave = ?",
                    (chave,)
                )
                invalidos += 1
                if invalidos <= 5:
                    print(f"   ❌ {chave[:25]}... → INVÁLIDO (não foi possível extrair)")
        
        except Exception as e:
            print(f"   ❌ Erro ao processar {chave[:25]}...: {e}")
            invalidos += 1
    
    # Commit
    conn.commit()
    
    # 3. Relatório
    print("\n📊 3. RELATÓRIO FINAL")
    print("-" * 80)
    print(f"   ✅ Corrigidos (arquivo existe): {corrigidos}")
    print(f"   ⚠️ Removidos (arquivo não existe): {removidos}")
    print(f"   ❌ Inválidos (não foi possível extrair): {invalidos}")
    print(f"   📝 Total processado: {len(registros_tupla)}")
    
    # 4. Verifica estado final
    print("\n🔍 4. VERIFICAÇÃO FINAL")
    print("-" * 80)
    
    cursor.execute("""
        SELECT COUNT(*)
        FROM xmls_baixados
        WHERE caminho_arquivo LIKE "(%)"
           OR caminho_arquivo LIKE "'%'"
    """)
    tuplas_restantes = cursor.fetchone()[0]
    
    if tuplas_restantes == 0:
        print("   ✅ Nenhuma tupla restante!")
    else:
        print(f"   ⚠️ Ainda restam {tuplas_restantes} tuplas (verificar manualmente)")
    
    # 5. Recomendações
    print("\n💡 5. PRÓXIMOS PASSOS")
    print("-" * 80)
    print("   1. Execute corrigir_forcado.py para atualizar xml_status")
    print("   2. Reinicie a interface para ver os ícones corrigidos")
    print("   3. Verifique se novas buscas agora registram caminhos corretamente")
    
    print("\n" + "=" * 80)
    print("✅ Correção concluída!")
    print("=" * 80)
    
    conn.close()

if __name__ == "__main__":
    main()
