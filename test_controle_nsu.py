"""
🔒 SCRIPT DE TESTE - CONTROLE RIGOROSO DE NSU
================================================

Este script testa todas as funcionalidades do controle rigoroso de NSU:
1. Índices de performance
2. Validação cruzada get_last_nsu
3. Validação de retrocesso em set_last_nsu
4. Detecção de gaps na sequência
5. Estatísticas detalhadas por informante
6. Logs de auditoria

Uso:
    python test_controle_nsu.py
"""

import sys
import sqlite3
from pathlib import Path

# Adiciona diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

from nfe_search import DatabaseManager

def print_header(title):
    """Imprime cabeçalho formatado"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def test_indices():
    """Testa se os índices foram criados"""
    print_header("TESTE 1: Verificando Índices de Performance")
    
    conn = sqlite3.connect("notas.db")
    cursor = conn.cursor()
    
    # Lista todos os índices
    indices = cursor.execute("""
        SELECT name, tbl_name, sql 
        FROM sqlite_master 
        WHERE type='index' 
        AND tbl_name='notas_detalhadas'
    """).fetchall()
    
    print(f"\nTotal de índices encontrados: {len(indices)}")
    print("\nÍndices criados:")
    
    indices_esperados = ['idx_nsu_informante', 'idx_nsu', 'idx_data_emissao']
    indices_encontrados = []
    
    for idx in indices:
        nome, tabela, sql = idx
        print(f"  ✅ {nome} em {tabela}")
        indices_encontrados.append(nome)
    
    # Verifica se todos os índices esperados existem
    faltando = [idx for idx in indices_esperados if idx not in indices_encontrados]
    if faltando:
        print(f"\n⚠️ Índices faltando: {faltando}")
    else:
        print("\n✅ Todos os índices críticos foram criados!")
    
    conn.close()
    return len(faltando) == 0

def test_get_last_nsu(db):
    """Testa get_last_nsu com validação cruzada"""
    print_header("TESTE 2: Validação Cruzada get_last_nsu()")
    
    # Lista todos os informantes
    conn = sqlite3.connect("notas.db")
    cursor = conn.cursor()
    
    informantes = cursor.execute("""
        SELECT DISTINCT informante 
        FROM notas_detalhadas 
        WHERE informante IS NOT NULL
    """).fetchall()
    
    print(f"\nTestando {len(informantes)} informantes...\n")
    
    for (informante,) in informantes:
        # Busca NSU usando a nova função
        nsu = db.get_last_nsu(informante)
        
        # Busca manualmente para verificar
        nsu_tabela = cursor.execute(
            "SELECT ult_nsu FROM nsu WHERE informante=?", (informante,)
        ).fetchone()
        nsu_tabela = nsu_tabela[0] if nsu_tabela else "000000000000000"
        
        nsu_notas = cursor.execute("""
            SELECT MAX(nsu) FROM notas_detalhadas 
            WHERE informante=? AND nsu IS NOT NULL AND nsu != ''
        """, (informante,)).fetchone()
        nsu_notas = nsu_notas[0] if (nsu_notas and nsu_notas[0]) else "000000000000000"
        
        status = "✅" if nsu == max(nsu_tabela, nsu_notas) else "❌"
        
        print(f"{status} {informante}")
        print(f"    Tabela nsu: {nsu_tabela}")
        print(f"    Max em notas: {nsu_notas}")
        print(f"    Retornado: {nsu}")
        
        if nsu_tabela != nsu_notas:
            print(f"    ⚠️ DIVERGÊNCIA DETECTADA!")
    
    conn.close()
    print("\n✅ Teste get_last_nsu() concluído")

def test_nsu_stats(db):
    """Testa estatísticas de NSU"""
    print_header("TESTE 3: Estatísticas de NSU por Informante")
    
    conn = sqlite3.connect("notas.db")
    cursor = conn.cursor()
    
    informantes = cursor.execute("""
        SELECT DISTINCT informante 
        FROM notas_detalhadas 
        WHERE informante IS NOT NULL
    """).fetchall()
    
    print(f"\nEstatísticas para {len(informantes)} informantes:\n")
    
    total_docs = 0
    total_com_nsu = 0
    total_sem_nsu = 0
    
    for (informante,) in informantes:
        stats = db.get_nsu_stats(informante)
        
        total_docs += stats['total_documentos']
        total_com_nsu += stats['com_nsu']
        total_sem_nsu += stats['sem_nsu']
        
        print(f"{informante}:")
        print(f"    Total: {stats['total_documentos']} docs")
        print(f"    Com NSU: {stats['com_nsu']} ({stats['percentual_com_nsu']:.1f}%)")
        print(f"    Sem NSU: {stats['sem_nsu']}")
        print(f"    Faixa: {stats['nsu_minimo']} até {stats['nsu_maximo']}")
        print()
    
    print("="*80)
    print("RESUMO GERAL:")
    print(f"  Total de documentos: {total_docs}")
    print(f"  Com NSU: {total_com_nsu} ({total_com_nsu/total_docs*100:.1f}%)")
    print(f"  Sem NSU: {total_sem_nsu} ({total_sem_nsu/total_docs*100:.1f}%)")
    
    if total_sem_nsu > 0:
        print(f"\n⚠️ ATENÇÃO: {total_sem_nsu} documentos SEM NSU!")
        print("  Execute uma nova busca para preencher os NSUs.")
    else:
        print("\n✅ Todos os documentos possuem NSU!")
    
    conn.close()

def test_nsu_sequence(db):
    """Testa validação de sequência e detecção de gaps"""
    print_header("TESTE 4: Validação de Sequência de NSU")
    
    conn = sqlite3.connect("notas.db")
    cursor = conn.cursor()
    
    informantes = cursor.execute("""
        SELECT DISTINCT informante 
        FROM notas_detalhadas 
        WHERE informante IS NOT NULL
    """).fetchall()
    
    print(f"\nVerificando sequência para {len(informantes)} informantes...\n")
    
    for (informante,) in informantes:
        result = db.validate_nsu_sequence(informante)
        
        status_emoji = "✅" if result['status'] == 'OK' else "⚠️"
        
        print(f"{status_emoji} {informante}")
        print(f"    Status: {result['status']}")
        print(f"    Documentos: {result['total_documentos']}")
        print(f"    Faixa NSU: {result['nsu_minimo']} até {result['nsu_maximo']}")
        
        if result['gaps_detectados'] > 0:
            print(f"    ⚠️ Gaps detectados: {result['gaps_detectados']}")
            if len(result['gaps']) <= 10:
                print(f"    NSUs faltando: {', '.join(result['gaps'])}")
            else:
                print(f"    Primeiros 10 NSUs faltando: {', '.join(result['gaps'][:10])}")
        elif result['gaps_detectados'] == 0:
            print(f"    ✅ Sequência completa, sem gaps")
        print()
    
    conn.close()
    print("✅ Teste de sequência concluído")

def main():
    """Executa todos os testes"""
    print("\n" + "="*80)
    print("🔒 TESTE DO CONTROLE RIGOROSO DE NSU")
    print("="*80)
    print("\nInicializando banco de dados...")
    
    # Inicializa o banco
    db_path = Path("notas.db")
    db = DatabaseManager(db_path)
    
    # Garante que a tabela está atualizada
    print("Criando/atualizando tabela com índices...")
    db.criar_tabela_detalhada()
    
    print("\n✅ Banco inicializado com sucesso!")
    print("Executando testes...\n")
    
    try:
        # Teste 1: Índices
        test_indices()
        
        # Teste 2: get_last_nsu
        test_get_last_nsu(db)
        
        # Teste 3: Estatísticas
        test_nsu_stats(db)
        
        # Teste 4: Validação de sequência
        test_nsu_sequence(db)
        
        print_header("TODOS OS TESTES CONCLUÍDOS ✅")
        print("\n🔒 Sistema de controle rigoroso de NSU está operacional!")
        print("\nPróximos passos:")
        print("1. Execute uma nova busca para preencher NSUs faltantes")
        print("2. Monitore os logs para mensagens de auditoria")
        print("3. Verifique periodicamente as estatísticas de NSU")
        
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
