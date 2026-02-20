# -*- coding: utf-8 -*-
"""
🧹 LIMPEZA URGENTE: Remove Eventos e Ciências dos Perfis de Armazenamento

PROBLEMA: Sistema estava salvando eventos/ciências nos perfis quando deveria
         salvar APENAS NF-e, CT-e e NFS-e completas.

SOLUÇÃO: Este script remove todos os arquivos indesejados dos perfis ativos.

Autor: Sistema
Data: 2026-02-20
"""
import sqlite3
import os
from pathlib import Path

def limpar_eventos_dos_perfis():
    """Remove eventos e ciências dos perfis de armazenamento"""
    
    print("="*80)
    print("🧹 LIMPEZA: Removendo Eventos e Ciências dos Perfis")
    print("="*80)
    print()
    
    # Conecta no banco para buscar perfis ativos
    db_path = Path(__file__).parent / "notas.db"
    
    if not db_path.exists():
        print("❌ Banco de dados não encontrado!")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Busca perfis ativos
    cursor.execute("""
        SELECT id, nome, pasta_base, organizacao_tipo
        FROM perfis_armazenamento
        WHERE ativo = 1
    """)
    
    perfis = cursor.fetchall()
    conn.close()
    
    if not perfis:
        print("⚠️ Nenhum perfil ativo encontrado")
        return
    
    print(f"📋 Encontrados {len(perfis)} perfil(is) ativo(s)")
    print()
    
    total_removidos = 0
    
    for perfil in perfis:
        perfil_id, nome, pasta_base, organizacao_tipo = perfil
        
        print(f"🔍 Analisando perfil: {nome}")
        print(f"   Pasta: {pasta_base}")
        print(f"   Organização: {organizacao_tipo}")
        print()
        
        pasta_perfil = Path(pasta_base)
        
        if not pasta_perfil.exists():
            print(f"   ⚠️ Pasta não existe, pulando...")
            print()
            continue
        
        removidos_perfil = 0
        
        # 🔍 BUSCA GLOBAL: Procura por TODOS os arquivos com EVENTO/CIENCIA no nome
        # independente da estrutura de pastas
        print(f"   🔍 Procurando arquivos com EVENTO/CIENCIA no nome...")
        
        arquivos_eventos = list(pasta_perfil.glob('**/*.xml'))
        arquivos_para_remover = []
        
        for arquivo in arquivos_eventos:
            nome = arquivo.name.upper()
            # Lista completa de palavras-chave que indicam eventos/ciências
            palavras_evento = [
                'EVENTO', 'CIENCIA', 'CONFIRMACAO', 
                'DESCONHECIMENTO', 'NAO_REALIZADA',
                'CANCELAMENTO', 'CARTA_CORRECAO'
            ]
            
            if any(palavra in nome for palavra in palavras_evento):
                arquivos_para_remover.append(arquivo)
        
        if arquivos_para_remover:
            print(f"   📊 Encontrados {len(arquivos_para_remover)} arquivo(s) de eventos")
            
            for arquivo in arquivos_para_remover:
                try:
                    print(f"      🗑️ Removendo: {arquivo.relative_to(pasta_perfil)}")
                    arquivo.unlink()
                    removidos_perfil += 1
                except Exception as e:
                    print(f"         ❌ Erro: {e}")
        else:
            print(f"   ✅ Nenhum evento encontrado")
        
        # Remove pastas vazias após limpeza
        print(f"   🧹 Limpando pastas vazias...")
        pastas_removidas = 0
        for subdir in sorted(pasta_perfil.rglob('*'), key=lambda x: len(str(x)), reverse=True):
            if subdir.is_dir():
                try:
                    if not list(subdir.iterdir()):
                        subdir.rmdir()
                        pastas_removidas += 1
                except:
                    pass
        
        if pastas_removidas > 0:
            print(f"   📁 {pastas_removidas} pasta(s) vazia(s) removida(s)")
        
        print(f"   ✅ Perfil '{nome}': {removidos_perfil} arquivo(s) removido(s)")
        print()
        
        total_removidos += removidos_perfil
    
    print("="*80)
    print(f"✅ LIMPEZA CONCLUÍDA: {total_removidos} arquivo(s) removido(s)")
    print("="*80)
    print()
    print("📌 APENAS xmls/backup/ ainda contém eventos (correto!)")
    print("📌 Perfis agora têm APENAS NF-e, CT-e e NFS-e completas")
    print()

if __name__ == '__main__':
    limpar_eventos_dos_perfis()
    input("\nPressione Enter para sair...")
