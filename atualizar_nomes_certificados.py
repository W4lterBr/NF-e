#!/usr/bin/env python3
"""
Script para atualizar os nomes dos certificados no banco de dados
baseado nas pastas do armazenamento configurado pelo usuário.
"""
import sqlite3
from pathlib import Path

def atualizar_nomes_certificados(db_path="notas.db", storage_path=None):
    """Atualiza campo nome_certificado baseado nas pastas de armazenamento"""
    
    if not storage_path:
        # Tenta buscar do banco
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT valor FROM config WHERE chave = 'storage_pasta_base'")
        row = cursor.fetchone()
        if row and row[0] and row[0] != 'xmls':
            storage_path = row[0]
        conn.close()
    
    if not storage_path or storage_path == 'xmls':
        print("❌ Nenhum caminho de armazenamento configurado (ou usando padrão 'xmls')")
        print("Configure o armazenamento no sistema antes de executar este script.")
        return
    
    print(f"📂 Verificando pastas em: {storage_path}")
    storage = Path(storage_path)
    
    if not storage.exists():
        print(f"❌ Pasta de armazenamento não existe: {storage_path}")
        return
    
    # Mapeia CNPJs para nomes de pastas
    mapeamento = {}
    pastas_cnpj_puro = []
    
    for pasta in storage.iterdir():
        if not pasta.is_dir():
            continue
        
        nome_pasta = pasta.name
        
        # Extrai CNPJ da pasta (14 dígitos)
        cnpj = ''.join(c for c in nome_pasta if c.isdigit())
        
        if len(cnpj) == 14:
            # Verifica se é pasta com nome amigável (ex: "61-MATPARCG") ou CNPJ puro
            if len(cnpj) == len(nome_pasta):
                # Pasta com apenas CNPJ (backup local)
                pastas_cnpj_puro.append((cnpj, nome_pasta))
            else:
                # Pasta com nome amigável contendo CNPJ
                mapeamento[cnpj] = nome_pasta
                print(f"   📁 {nome_pasta} → CNPJ: {cnpj}")
    
    if not mapeamento and pastas_cnpj_puro:
        print("\n⚠️ Apenas pastas com CNPJ puro encontradas.")
        print("   Essas são pastas de backup local, não de armazenamento.")
        print("\n   Pastas encontradas:")
        for cnpj, nome in pastas_cnpj_puro:
            print(f"      • {nome}")
        print("\n💡 Use o padrão de nomes amigáveis no armazenamento:")
        print("   Exemplo: 61-MATPARCG, 79-ALFA COMPUTADORES, etc.")
        return
    
    if not mapeamento:
        print("❌ Nenhuma pasta com CNPJ encontrada no armazenamento")
        return
    
    print(f"\n✅ {len(mapeamento)} certificados identificados")
    print("\n🔄 Atualizando banco de dados...")
    
    # Atualiza banco de dados
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    atualizados = 0
    
    for cnpj, nome_pasta in mapeamento.items():
        # Atualiza por informante (que deve ser o CNPJ)
        cursor.execute(
            "UPDATE certificados SET nome_certificado = ? WHERE informante = ?",
            (nome_pasta, cnpj)
        )
        
        # Também tenta por cnpj_cpf
        cursor.execute(
            "UPDATE certificados SET nome_certificado = ? WHERE cnpj_cpf = ?",
            (nome_pasta, cnpj)
        )
        
        if cursor.rowcount > 0:
            print(f"   ✅ {nome_pasta} ({cnpj})")
            atualizados += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ {atualizados} certificados atualizados no banco!")
    print("\n💡 Agora os XMLs serão salvos nas pastas corretas do armazenamento.")

if __name__ == "__main__":
    import sys
    
    storage_path = sys.argv[1] if len(sys.argv) > 1 else None
    atualizar_nomes_certificados(storage_path=storage_path)
