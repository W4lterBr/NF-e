"""
Teste dos métodos de manifestação no DatabaseManager.
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from nfe_search import DatabaseManager

def test_manifestacao_methods():
    """Testa os métodos de manifestação"""
    
    print("=" * 60)
    print("TESTE DOS MÉTODOS DE MANIFESTAÇÃO")
    print("=" * 60)
    
    # Inicializa banco de testes
    db_path = BASE_DIR / "notas_test.db"
    print(f"\n📂 Usando banco: {db_path}")
    
    db = DatabaseManager(db_path)
    print("✅ DatabaseManager inicializado")
    
    # Testa dados
    chave_teste = "50260129506480000149550010001498511002767460"
    tipo_evento = "210210"  # Ciência da Operação
    informante = "33251845000109"
    
    print(f"\n📋 Dados de teste:")
    print(f"   Chave: {chave_teste}")
    print(f"   Tipo Evento: {tipo_evento}")
    print(f"   Informante: {informante}")
    
    # Teste 1: Verificar se método existe
    print("\n🔍 Teste 1: Verificando se método existe...")
    if hasattr(db, 'check_manifestacao_exists'):
        print("   ✅ Método check_manifestacao_exists EXISTE")
    else:
        print("   ❌ Método check_manifestacao_exists NÃO EXISTE")
        return False
    
    if hasattr(db, 'register_manifestacao'):
        print("   ✅ Método register_manifestacao EXISTE")
    else:
        print("   ❌ Método register_manifestacao NÃO EXISTE")
        return False
    
    # Teste 2: Verificar se manifestação existe (deve retornar False)
    print("\n🔍 Teste 2: Verificando se manifestação existe (esperado: False)...")
    exists = db.check_manifestacao_exists(chave_teste, tipo_evento, informante)
    print(f"   Resultado: {exists}")
    if not exists:
        print("   ✅ Correto - manifestação não existe")
    else:
        print("   ⚠️ Manifestação já existe no banco")
    
    # Teste 3: Registrar manifestação
    print("\n📝 Teste 3: Registrando manifestação...")
    success = db.register_manifestacao(
        chave=chave_teste,
        tipo_evento=tipo_evento,
        informante=informante,
        status='TESTE',
        protocolo='999888777666555'
    )
    if success:
        print("   ✅ Manifestação registrada com sucesso")
    else:
        print("   ⚠️ Falha ao registrar ou já existe")
    
    # Teste 4: Verificar novamente (agora deve retornar True)
    print("\n🔍 Teste 4: Verificando se manifestação existe agora (esperado: True)...")
    exists = db.check_manifestacao_exists(chave_teste, tipo_evento, informante)
    print(f"   Resultado: {exists}")
    if exists:
        print("   ✅ Correto - manifestação encontrada")
    else:
        print("   ❌ ERRO - manifestação deveria existir")
        return False
    
    # Teste 5: Tentar registrar duplicata (deve falhar)
    print("\n📝 Teste 5: Tentando registrar duplicata (esperado: False)...")
    success = db.register_manifestacao(
        chave=chave_teste,
        tipo_evento=tipo_evento,
        informante=informante,
        status='TESTE2',
        protocolo='111222333444555'
    )
    if not success:
        print("   ✅ Correto - duplicata rejeitada")
    else:
        print("   ❌ ERRO - não deveria permitir duplicata")
        return False
    
    # Teste 6: Verificar tabela diretamente
    print("\n🔍 Teste 6: Verificando dados na tabela manifestacoes...")
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT * FROM manifestacoes WHERE chave = ? AND tipo_evento = ? AND informante = ?",
        (chave_teste, tipo_evento, informante)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        print(f"   ✅ Registro encontrado:")
        print(f"      ID: {row[0]}")
        print(f"      Chave: {row[1]}")
        print(f"      Tipo Evento: {row[2]}")
        print(f"      Informante: {row[3]}")
        print(f"      Data: {row[4]}")
        print(f"      Status: {row[5]}")
        print(f"      Protocolo: {row[6]}")
    else:
        print("   ❌ ERRO - registro não encontrado na tabela")
        return False
    
    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_manifestacao_methods()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERRO DURANTE TESTE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
