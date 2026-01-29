"""
Script para corrigir registros na tabela xmls_baixados que estão sem caminho_arquivo.
Procura os XMLs salvos em disco e atualiza o banco com os caminhos corretos.
"""

import sqlite3
import os
from pathlib import Path

def encontrar_xml(chave, base_path="xmls"):
    """
    Procura um XML pela chave em toda a estrutura de pastas.
    
    Args:
        chave: Chave de acesso (44 dígitos)
        base_path: Pasta base onde procurar
    
    Returns:
        str: Caminho absoluto do XML encontrado, ou None
    """
    base_path = Path(base_path)
    if not base_path.exists():
        return None
    
    # Procura recursivamente por arquivos com a chave no nome
    for xml_file in base_path.rglob(f"{chave}.xml"):
        if xml_file.is_file():
            return str(xml_file.absolute())
    
    return None

def corrigir_caminhos_xmls():
    """Corrige os caminhos dos XMLs na tabela xmls_baixados."""
    
    db_path = Path("notas.db")
    if not db_path.exists():
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return
    
    print(f"🔍 Conectando ao banco: {db_path}")
    
    with sqlite3.connect(str(db_path)) as conn:
        # Busca todos os registros sem caminho_arquivo
        cursor = conn.execute("""
            SELECT chave, cnpj_cpf 
            FROM xmls_baixados 
            WHERE caminho_arquivo IS NULL OR caminho_arquivo = ''
        """)
        
        registros_sem_caminho = cursor.fetchall()
        total = len(registros_sem_caminho)
        
        if total == 0:
            print("✅ Todos os registros já têm caminho_arquivo preenchido!")
            return
        
        print(f"📊 Encontrados {total} registros sem caminho_arquivo")
        print(f"🔎 Procurando XMLs em disco...\n")
        
        encontrados = 0
        nao_encontrados = 0
        
        for chave, cnpj in registros_sem_caminho:
            # Procura o XML em xmls/
            caminho = encontrar_xml(chave, "xmls")
            
            if caminho:
                # Atualiza o banco
                conn.execute("""
                    UPDATE xmls_baixados 
                    SET caminho_arquivo = ?, baixado_em = datetime('now')
                    WHERE chave = ?
                """, (caminho, chave))
                
                encontrados += 1
                print(f"✅ [{encontrados}/{total}] {chave[:20]}... → {caminho}")
            else:
                nao_encontrados += 1
                print(f"❌ [{encontrados + nao_encontrados}/{total}] {chave[:20]}... → Não encontrado")
        
        conn.commit()
        
        print(f"\n{'='*80}")
        print(f"📊 RESULTADO:")
        print(f"   ✅ XMLs encontrados e atualizados: {encontrados}")
        print(f"   ❌ XMLs não encontrados: {nao_encontrados}")
        print(f"   📈 Taxa de sucesso: {(encontrados/total*100):.1f}%")
        print(f"{'='*80}")

if __name__ == "__main__":
    print("=" * 80)
    print("CORREÇÃO DE CAMINHOS NA TABELA xmls_baixados")
    print("=" * 80)
    print()
    
    corrigir_caminhos_xmls()
    
    print()
    print("🎯 Após executar este script, as notas devem aparecer como COMPLETO")
    print("   na interface, pois agora o banco sabe onde os XMLs estão salvos.")
