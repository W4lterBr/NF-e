"""
Script de teste para módulo NFS-e
Verifica funcionalidades básicas e configurações
"""

import sys
import io
from pathlib import Path

# Força UTF-8 no stdout para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Adiciona diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

from nfse_search import (
    logger,
    NFSeDatabase,
    consultar_cnpj,
    buscar_codigo_ibge,
    PROVEDORES_NFSE,
    URLS_MUNICIPIOS
)

def teste_banco_dados():
    """Testa conexão e estrutura do banco de dados."""
    print("\n" + "="*60)
    print("TESTE 1: Banco de Dados NFS-e")
    print("="*60)
    
    try:
        db = NFSeDatabase()
        print("✅ Banco de dados inicializado com sucesso")
        
        # Lista certificados
        certificados = db.get_certificados()
        print(f"\n📋 Certificados cadastrados: {len(certificados)}")
        
        for idx, cert in enumerate(certificados, 1):
            cnpj, path, senha, informante, cuf = cert
            print(f"\n   {idx}. CNPJ: {cnpj}")
            print(f"      Informante: {informante}")
            print(f"      Certificado: {path}")
            print(f"      cUF: {cuf}")
            
            # Verifica se tem config de NFS-e
            configs = db.get_config_nfse(cnpj)
            if configs:
                print(f"      ✅ Tem {len(configs)} configuração(ões) de NFS-e")
                for config in configs:
                    provedor, cod_mun, insc_mun, url = config
                    print(f"         - Provedor: {provedor}")
                    print(f"         - Município: {cod_mun}")
                    print(f"         - Inscrição: {insc_mun}")
            else:
                print(f"      ⚠️  Sem configuração de NFS-e")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar banco de dados: {e}")
        import traceback
        traceback.print_exc()
        return False


def teste_provedores():
    """Lista provedores conhecidos."""
    print("\n" + "="*60)
    print("TESTE 2: Provedores de NFS-e")
    print("="*60)
    
    print(f"\n📋 {len(PROVEDORES_NFSE)} provedor(es) configurado(s):\n")
    
    for codigo, info in PROVEDORES_NFSE.items():
        print(f"   • {info['nome']} ({codigo})")
        print(f"     {info['descricao']}")
        print(f"     URL: {info.get('url_base', 'N/A')}")
        print()


def teste_municipios():
    """Lista municípios configurados."""
    print("\n" + "="*60)
    print("TESTE 3: Municípios Configurados")
    print("="*60)
    
    print(f"\n📋 {len(URLS_MUNICIPIOS)} município(s) com URLs configuradas:\n")
    
    for cod_ibge, info in URLS_MUNICIPIOS.items():
        print(f"   • {info['nome']}/{info['uf']} (IBGE: {cod_ibge})")
        print(f"     Provedor: {info.get('provedor', 'N/A')}")
        print(f"     Tipo API: {info.get('tipo_api', 'SOAP')}")
        print(f"     Versão: {info.get('versao', 'N/A')}")
        print(f"     URLs: {len(info.get('urls', []))} endpoint(s)")
        print()


def teste_consulta_cnpj():
    """Testa consulta de CNPJ."""
    print("\n" + "="*60)
    print("TESTE 4: Consulta de CNPJ (Opcional)")
    print("="*60)
    
    cnpj_teste = input("\n Digite um CNPJ para testar (ou Enter para pular): ").strip()
    
    if not cnpj_teste:
        print("⏭️  Teste pulado")
        return True
    
    try:
        print(f"\n🔍 Consultando CNPJ: {cnpj_teste}")
        resultado = consultar_cnpj(cnpj_teste)
        
        if resultado.get('sucesso'):
            print("\n✅ Consulta bem-sucedida!")
            print(f"   Razão Social: {resultado.get('razao_social')}")
            print(f"   Município: {resultado.get('municipio')}/{resultado.get('uf')}")
            print(f"   Código IBGE: {resultado.get('codigo_ibge')}")
            return True
        else:
            print(f"\n⚠️  Consulta falhou: {resultado.get('mensagem')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Erro na consulta: {e}")
        return False


def teste_nuvem_fiscal():
    """Verifica se Nuvem Fiscal está configurada."""
    print("\n" + "="*60)
    print("TESTE 5: Nuvem Fiscal API")
    print("="*60)
    
    try:
        from nuvem_fiscal_api import NuvemFiscalAPI
        print("\n✅ Módulo nuvem_fiscal_api importado com sucesso")
        
        # Verifica se tem credenciais
        api_credentials_path = Path(__file__).parent / "api_credentials.csv"
        
        if api_credentials_path.exists():
            print(f"✅ Arquivo de credenciais encontrado: {api_credentials_path}")
            
            # Lê credenciais
            with open(api_credentials_path, 'r') as f:
                linhas = f.readlines()
                print(f"   {len(linhas)} linha(s) de credenciais")
                
                if len(linhas) > 1:  # Tem header + dados
                    print("\n   Formato esperado: cnpj,client_id,client_secret")
                    print("   ✅ Credenciais parecem estar configuradas")
                else:
                    print("   ⚠️  Arquivo vazio ou só com header")
        else:
            print(f"⚠️  Arquivo de credenciais não encontrado: {api_credentials_path}")
            print("   Para usar Nuvem Fiscal, crie o arquivo com formato:")
            print("   cnpj,client_id,client_secret")
            print("   12345678901234,seu_client_id,seu_client_secret")
        
        return True
        
    except ImportError as e:
        print(f"⚠️  Módulo nuvem_fiscal_api não encontrado: {e}")
        print("   Este módulo é opcional para consultas via Nuvem Fiscal")
        return True
    except Exception as e:
        print(f"❌ Erro ao verificar Nuvem Fiscal: {e}")
        return False


def menu_configuracao():
    """Menu para configurar NFS-e de um certificado."""
    print("\n" + "="*60)
    print("CONFIGURAÇÃO: Adicionar NFS-e a um certificado")
    print("="*60)
    
    db = NFSeDatabase()
    certificados = db.get_certificados()
    
    if not certificados:
        print("\n❌ Nenhum certificado cadastrado no sistema!")
        print("   Adicione certificados primeiro através da interface principal")
        return
    
    print("\n📋 Certificados disponíveis:\n")
    for idx, cert in enumerate(certificados, 1):
        cnpj, _, _, informante, _ = cert
        print(f"   {idx}. {informante} (CNPJ: {cnpj})")
    
    try:
        escolha = input("\n Escolha o número do certificado (ou Enter para cancelar): ").strip()
        
        if not escolha:
            print("⏭️  Cancelado")
            return
        
        idx_escolhido = int(escolha) - 1
        if idx_escolhido < 0 or idx_escolhido >= len(certificados):
            print("❌ Escolha inválida!")
            return
        
        cert_escolhido = certificados[idx_escolhido]
        cnpj, _, _, informante, _ = cert_escolhido
        
        print(f"\n✅ Certificado selecionado: {informante}")
        
        # Consulta dados do CNPJ
        print("\n🔍 Consultando dados do CNPJ...")
        dados = consultar_cnpj(cnpj)
        
        if dados.get('sucesso'):
            municipio = dados.get('municipio')
            uf = dados.get('uf')
            cod_ibge = dados.get('codigo_ibge')
            
            print(f"\n✅ Município: {municipio}/{uf}")
            print(f"   Código IBGE: {cod_ibge}")
            
            # Verifica se tem URL configurada
            if cod_ibge in URLS_MUNICIPIOS:
                info_mun = URLS_MUNICIPIOS[cod_ibge]
                print(f"\n✅ Município tem configuração pré-definida!")
                print(f"   Provedor sugerido: {info_mun.get('provedor')}")
                print(f"   Tipo: {info_mun.get('tipo_api', 'SOAP')}")
            else:
                print(f"\n⚠️  Município {municipio} não tem configuração pré-definida")
                print("   Será necessário configurar manualmente")
            
            # Solicita inscrição municipal
            inscricao = input("\n Digite a Inscrição Municipal (ou Enter para pular): ").strip()
            
            if not inscricao:
                print("⏭️  Configuração cancelada")
                return
            
            # Salva configuração
            provedor = URLS_MUNICIPIOS.get(cod_ibge, {}).get('provedor', 'GINFES')
            db.adicionar_config_nfse(cnpj, provedor, cod_ibge, inscricao)
            
            print("\n✅ Configuração NFS-e salva com sucesso!")
            print(f"   CNPJ: {cnpj}")
            print(f"   Município: {municipio}/{uf} ({cod_ibge})")
            print(f"   Provedor: {provedor}")
            print(f"   Inscrição: {inscricao}")
        
    except ValueError:
        print("❌ Entrada inválida!")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Executa todos os testes."""
    print("\n" + "="*70)
    print("TESTE DO MÓDULO NFS-e - Busca de Notas Fiscais de Serviço")
    print("="*70)
    
    # Executa testes
    teste_banco_dados()
    teste_provedores()
    teste_municipios()
    teste_nuvem_fiscal()
    teste_consulta_cnpj()
    
    # Menu de configuração
    print("\n" + "="*60)
    resposta = input("\n Deseja configurar NFS-e para algum certificado? (s/N): ").strip().lower()
    
    if resposta == 's':
        menu_configuracao()
    
    print("\n" + "="*70)
    print("TESTES CONCLUÍDOS!")
    print("="*70)
    print("\n📚 Próximos passos:")
    print("   1. Configure NFS-e para seus certificados (se necessário)")
    print("   2. Use a interface principal para fazer buscas automáticas")
    print("   3. Verifique logs em: logs/busca_nfse_*.log")
    print("\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
