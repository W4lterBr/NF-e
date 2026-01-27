"""
Teste de múltiplos eventos consecutivos.
Simula o cenário real do log onde múltiplos eventos são processados.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from nfe_search import DatabaseManager

def test_multiplos_eventos():
    """Testa processamento de múltiplos eventos"""
    
    print("=" * 60)
    print("TESTE DE MÚLTIPLOS EVENTOS CONSECUTIVOS")
    print("=" * 60)
    
    db_path = BASE_DIR / "notas_test.db"
    db = DatabaseManager(db_path)
    
    # Limpa registros anteriores de teste
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM manifestacoes WHERE informante = '33251845000109'")
    conn.commit()
    conn.close()
    print("\n🧹 Banco limpo para teste")
    
    # Simula 10 eventos diferentes
    eventos = [
        ("50251033251845000109550010000291791223004302", "210210", "NSU059028"),
        ("50251033251845000109550010000291801744936565", "210210", "NSU059032"),
        ("50251033251845000109550010000291911275636045", "210210", "NSU059036"),
        ("50251033251845000109550010000291941361359528", "210210", "NSU059037"),
        ("50251033251845000109550010000291931570773087", "210210", "NSU059038"),
        ("50251033251845000109550010000291831461359881", "210210", "NSU059039"),
        ("50251033251845000109550010000291761970528398", "210210", "NSU059040"),
        ("50251033251845000109550010000291701223004311", "210210", "NSU059041"),
        ("50251033251845000109550010000291641970528405", "210210", "NSU059045"),
        ("50251033251845000109550010000291821744936574", "210210", "NSU059046"),
    ]
    
    informante = "33251845000109"
    erros = 0
    sucessos = 0
    
    print(f"\n🔄 Processando {len(eventos)} eventos...")
    
    for chave, tipo_evento, nsu in eventos:
        try:
            # Simula o código real do nfe_search.py
            cStat_evento = '135'  # Evento registrado
            protocolo = f'150260000{nsu[3:]}'
            
            if tipo_evento.startswith('2102'):  # Manifestações
                if cStat_evento == '135':
                    if not db.check_manifestacao_exists(chave, tipo_evento, informante):
                        db.register_manifestacao(chave, tipo_evento, informante, 'REGISTRADA', protocolo)
                        print(f"   ✅ [{informante}] Manifestação {tipo_evento} registrada para {nsu}")
                        sucessos += 1
                    else:
                        print(f"   ℹ️ [{informante}] Manifestação já existe para {nsu}")
        except AttributeError as e:
            print(f"   ❌ [{informante}] ERRO ao processar {nsu}: {e}")
            erros += 1
        except Exception as e:
            print(f"   ❌ [{informante}] ERRO inesperado ao processar {nsu}: {e}")
            erros += 1
    
    # Verifica resultados
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT COUNT(*) FROM manifestacoes WHERE informante = ?",
        (informante,)
    )
    total_registrado = cursor.fetchone()[0]
    conn.close()
    
    print(f"\n📊 Resultados:")
    print(f"   Eventos processados: {len(eventos)}")
    print(f"   Sucessos: {sucessos}")
    print(f"   Erros: {erros}")
    print(f"   Total no banco: {total_registrado}")
    
    if erros == 0 and total_registrado == len(eventos):
        print("\n" + "=" * 60)
        print("✅ TESTE COMPLETO BEM-SUCEDIDO!")
        print("   - Nenhum erro de 'check_manifestacao_exists'")
        print("   - Todas as manifestações registradas")
        print("=" * 60)
        return True
    else:
        print("\n❌ TESTE FALHOU")
        return False

if __name__ == "__main__":
    try:
        success = test_multiplos_eventos()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
