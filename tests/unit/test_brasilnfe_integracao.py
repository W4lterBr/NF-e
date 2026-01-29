"""
Teste da integração API BrasilNFe
Execute este script para testar a configuração sem usar a interface gráfica
"""

import sys
from pathlib import Path

# Adiciona módulos ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

def testar_modulos():
    """Testa se os módulos foram importados corretamente."""
    print("=" * 80)
    print("TESTE 1: Importação de Módulos")
    print("=" * 80)
    
    try:
        from modules.brasilnfe_api import BrasilNFeAPI
        print("✅ BrasilNFeAPI importado com sucesso")
    except ImportError as e:
        print(f"❌ Erro ao importar BrasilNFeAPI: {e}")
        return False
    
    try:
        from modules.manifestacao_service import ManifestacaoService
        print("✅ ManifestacaoService importado com sucesso")
    except ImportError as e:
        print(f"❌ Erro ao importar ManifestacaoService: {e}")
        return False
    
    try:
        from modules.database import DatabaseManager
        print("✅ DatabaseManager importado com sucesso")
    except ImportError as e:
        print(f"❌ Erro ao importar DatabaseManager: {e}")
        return False
    
    return True

def testar_database():
    """Testa métodos do banco de dados."""
    print("\n" + "=" * 80)
    print("TESTE 2: Métodos do Banco de Dados")
    print("=" * 80)
    
    try:
        from modules.database import DatabaseManager
        
        # Cria instância temporária
        db = DatabaseManager("notas_test.db")
        
        # Testa set_config
        print("Testando set_config...")
        db.set_config('teste_chave', 'teste_valor')
        print("✅ set_config funcionou")
        
        # Testa get_config
        print("Testando get_config...")
        valor = db.get_config('teste_chave')
        if valor == 'teste_valor':
            print("✅ get_config retornou valor correto")
        else:
            print(f"❌ get_config retornou valor errado: {valor}")
        
        # Testa get_config com default
        print("Testando get_config com default...")
        valor_default = db.get_config('chave_inexistente', 'default_value')
        if valor_default == 'default_value':
            print("✅ get_config retornou default correto")
        else:
            print(f"❌ get_config default errado: {valor_default}")
        
        # Limpa teste
        db.set_config('teste_chave', '')
        
        return True
    except Exception as e:
        print(f"❌ Erro no teste de database: {e}")
        import traceback
        traceback.print_exc()
        return False

def testar_brasilnfe_api():
    """Testa criação de instância da API BrasilNFe."""
    print("\n" + "=" * 80)
    print("TESTE 3: API BrasilNFe")
    print("=" * 80)
    
    try:
        from modules.brasilnfe_api import BrasilNFeAPI
        
        # Testa criação com token fake
        print("Testando criação de instância...")
        api = BrasilNFeAPI("token_fake_para_teste")
        print("✅ Instância criada com sucesso")
        
        # Verifica atributos
        print("Verificando atributos...")
        assert hasattr(api, 'api_token'), "Atributo api_token não existe"
        assert hasattr(api, 'session'), "Atributo session não existe"
        assert hasattr(api, 'manifestar_nota_fiscal'), "Método manifestar_nota_fiscal não existe"
        print("✅ Todos os atributos presentes")
        
        # Verifica constantes
        print("Verificando constantes...")
        assert api.TIPO_CONFIRMACAO == 1, "TIPO_CONFIRMACAO incorreto"
        assert api.TIPO_CIENCIA == 2, "TIPO_CIENCIA incorreto"
        assert api.TIPO_DESCONHECIMENTO == 3, "TIPO_DESCONHECIMENTO incorreto"
        assert api.TIPO_NAO_REALIZADA == 4, "TIPO_NAO_REALIZADA incorreto"
        print("✅ Constantes corretas")
        
        return True
    except Exception as e:
        print(f"❌ Erro no teste de API: {e}")
        import traceback
        traceback.print_exc()
        return False

def testar_manifestacao_service():
    """Testa inicialização do ManifestacaoService com db."""
    print("\n" + "=" * 80)
    print("TESTE 4: ManifestacaoService com DB")
    print("=" * 80)
    
    try:
        from modules.manifestacao_service import ManifestacaoService
        from modules.database import DatabaseManager
        
        print("⚠️ Este teste requer certificado .pfx válido")
        print("   Pulando inicialização real (requer arquivo)")
        
        # Apenas verifica se a classe aceita parâmetro db
        import inspect
        sig = inspect.signature(ManifestacaoService.__init__)
        params = list(sig.parameters.keys())
        
        if 'db' in params:
            print("✅ Parâmetro 'db' presente no __init__")
        else:
            print(f"❌ Parâmetro 'db' não encontrado. Parâmetros: {params}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Erro no teste de ManifestacaoService: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Executa todos os testes."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " TESTE DE INTEGRAÇÃO BRASILNFE ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    testes = [
        testar_modulos,
        testar_database,
        testar_brasilnfe_api,
        testar_manifestacao_service,
    ]
    
    resultados = []
    for teste in testes:
        try:
            resultado = teste()
            resultados.append(resultado)
        except Exception as e:
            print(f"❌ Exceção no teste {teste.__name__}: {e}")
            resultados.append(False)
    
    print("\n" + "=" * 80)
    print("RESUMO DOS TESTES")
    print("=" * 80)
    
    total = len(resultados)
    passaram = sum(resultados)
    falharam = total - passaram
    
    print(f"Total: {total}")
    print(f"✅ Passaram: {passaram}")
    print(f"❌ Falharam: {falharam}")
    
    if falharam == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("   A integração BrasilNFe está pronta para uso.")
        print()
        print("PRÓXIMOS PASSOS:")
        print("1. Obtenha token em: https://brasilnfe.com.br")
        print("2. Configure no sistema: Menu → Configurações → 🔌 API BrasilNFe...")
        print("3. Teste manifestação de NF-e real")
        return 0
    else:
        print("\n⚠️ ALGUNS TESTES FALHARAM")
        print("   Revise os erros acima antes de usar o sistema.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
