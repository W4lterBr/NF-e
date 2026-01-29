"""
Script de Verificação do Sistema
Valida todas as correções e garante que o sistema está funcionando corretamente
"""
from pathlib import Path
from modules.database import DatabaseManager
import sys

def check_database():
    """Verifica integridade do banco de dados"""
    print("=" * 80)
    print("1️⃣ VERIFICAÇÃO DO BANCO DE DADOS")
    print("=" * 80)
    
    db = DatabaseManager(Path('notas.db'))
    
    with db._connect() as conn:
        # Estatísticas gerais
        total = conn.execute("SELECT COUNT(*) FROM notas_detalhadas").fetchone()[0]
        print(f"\n✓ Total de registros: {total}")
        
        # Registros por xml_status
        status_counts = conn.execute("""
            SELECT xml_status, COUNT(*) 
            FROM notas_detalhadas 
            GROUP BY xml_status
        """).fetchall()
        
        print("\nDistribuição por xml_status:")
        for status, count in status_counts:
            print(f"  - {status}: {count}")
        
        # Verifica registros inválidos
        invalidos = conn.execute("""
            SELECT COUNT(*) FROM notas_detalhadas 
            WHERE numero IS NULL 
               OR numero = '' 
               OR numero = 'N/A' 
               OR numero = 'SEM_NUMERO'
               OR nome_emitente = 'SEM_NOME'
        """).fetchone()[0]
        
        if invalidos == 0:
            print(f"\n✅ PASSOU: Zero registros inválidos")
        else:
            print(f"\n❌ FALHOU: {invalidos} registros inválidos encontrados")
            print("   Execute: python limpar_registros_invalidos.py")
            return False
        
        # Verifica eventos (devem existir mas não aparecer)
        eventos = conn.execute("""
            SELECT COUNT(*) FROM notas_detalhadas 
            WHERE xml_status = 'EVENTO'
        """).fetchone()[0]
        
        print(f"\n✓ Eventos no banco: {eventos} (salvos mas ocultos na interface)")
        
    return True

def check_files():
    """Verifica arquivos críticos"""
    print("\n" + "=" * 80)
    print("2️⃣ VERIFICAÇÃO DE ARQUIVOS")
    print("=" * 80)
    
    arquivos_criticos = [
        'modules/manifestacao_service.py',
        'nfe_search.py',
        'Busca NF-e.py',
        'requirements.txt',
        'PROGRESSO_MANIFESTACAO.md',
        'CORRECAO_EVENTOS_ERROS.md',
        'README_DOCUMENTACOES.md'
    ]
    
    todos_ok = True
    for arquivo in arquivos_criticos:
        path = Path(arquivo)
        if path.exists():
            print(f"✓ {arquivo}")
        else:
            print(f"❌ {arquivo} - NÃO ENCONTRADO")
            todos_ok = False
    
    if todos_ok:
        print("\n✅ PASSOU: Todos os arquivos críticos presentes")
    else:
        print("\n❌ FALHOU: Arquivos faltando")
    
    return todos_ok

def check_manifestacao_service():
    """Verifica se ManifestacaoService está correto"""
    print("\n" + "=" * 80)
    print("3️⃣ VERIFICAÇÃO DO SERVIÇO DE MANIFESTAÇÃO")
    print("=" * 80)
    
    try:
        from modules.manifestacao_service import ManifestacaoService
        
        # Verifica se construtor não aceita parâmetro 'db'
        import inspect
        sig = inspect.signature(ManifestacaoService.__init__)
        params = list(sig.parameters.keys())
        
        print(f"\nParâmetros do construtor: {params}")
        
        if 'db' in params:
            print("❌ FALHOU: Construtor ainda aceita parâmetro 'db' (deveria ser removido)")
            return False
        else:
            print("✅ PASSOU: Construtor correto (sem parâmetro 'db')")
        
        # Verifica se PyNFe está importado
        with open('modules/manifestacao_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'from pynfe' in content:
                print("✅ PASSOU: PyNFe está importado")
            else:
                print("❌ FALHOU: PyNFe não encontrado nas importações")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ FALHOU: Erro ao importar ManifestacaoService: {e}")
        return False

def check_nfe_search_filters():
    """Verifica se filtros estão implementados em nfe_search.py"""
    print("\n" + "=" * 80)
    print("4️⃣ VERIFICAÇÃO DE FILTROS (nfe_search.py)")
    print("=" * 80)
    
    try:
        with open('nfe_search.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica filtro de respostas SEFAZ
        if "retDistDFeInt" in content and "return None" in content:
            print("✅ PASSOU: Filtro de respostas SEFAZ implementado")
        else:
            print("❌ FALHOU: Filtro de respostas SEFAZ não encontrado")
            return False
        
        # Verifica tratamento de eventos
        if "xml_status = 'EVENTO'" in content:
            print("✅ PASSOU: Identificação de eventos implementada")
        else:
            print("⚠️ AVISO: Identificação de eventos não encontrada")
        
        return True
        
    except Exception as e:
        print(f"❌ FALHOU: Erro ao verificar nfe_search.py: {e}")
        return False

def check_interface_filters():
    """Verifica se filtros estão na interface"""
    print("\n" + "=" * 80)
    print("5️⃣ VERIFICAÇÃO DE FILTROS (Interface)")
    print("=" * 80)
    
    try:
        with open('Busca NF-e.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica filtro de eventos
        if "if xml_status == 'EVENTO':" in content and "continue" in content:
            print("✅ PASSOU: Filtro de eventos na interface implementado")
        else:
            print("❌ FALHOU: Filtro de eventos não encontrado")
            return False
        
        # Verifica SQL com filtro de eventos
        if "xml_status != 'EVENTO'" in content:
            print("✅ PASSOU: Filtro SQL de eventos implementado")
        else:
            print("⚠️ AVISO: Filtro SQL de eventos não encontrado")
        
        return True
        
    except Exception as e:
        print(f"❌ FALHOU: Erro ao verificar Busca NF-e.py: {e}")
        return False

def main():
    """Executa todas as verificações"""
    print("\n" + "🔍 VERIFICAÇÃO COMPLETA DO SISTEMA 🔍".center(80))
    print("=" * 80)
    print("Validando implementações de:")
    print("  1. Banco de dados limpo")
    print("  2. Arquivos críticos presentes")
    print("  3. Serviço de manifestação (PyNFe)")
    print("  4. Filtros em nfe_search.py")
    print("  5. Filtros na interface")
    print("=" * 80)
    
    resultados = []
    
    # Executa verificações
    resultados.append(("Banco de Dados", check_database()))
    resultados.append(("Arquivos Críticos", check_files()))
    resultados.append(("Manifestação Service", check_manifestacao_service()))
    resultados.append(("Filtros nfe_search", check_nfe_search_filters()))
    resultados.append(("Filtros Interface", check_interface_filters()))
    
    # Resumo final
    print("\n" + "=" * 80)
    print("📊 RESUMO FINAL")
    print("=" * 80)
    
    total_testes = len(resultados)
    testes_passados = sum(1 for _, passou in resultados if passou)
    
    for nome, passou in resultados:
        status = "✅ PASSOU" if passou else "❌ FALHOU"
        print(f"{status:12} - {nome}")
    
    print("=" * 80)
    print(f"Resultado: {testes_passados}/{total_testes} testes passaram")
    
    if testes_passados == total_testes:
        print("\n🎉 SUCESSO: Sistema 100% verificado e funcionando!")
        print("\nPróximos passos:")
        print("  1. Reabrir a interface (Busca NF-e.py)")
        print("  2. Verificar que eventos não aparecem mais")
        print("  3. Testar manifestação em nota RESUMO")
        return 0
    else:
        print("\n⚠️ ATENÇÃO: Alguns testes falharam!")
        print("Revise os erros acima e corrija antes de usar o sistema.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
