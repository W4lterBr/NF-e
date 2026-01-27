"""
Teste de busca real de NFS-e usando Nuvem Fiscal API
"""

import sys
import io
from pathlib import Path
from datetime import datetime, timedelta

# Força UTF-8 no stdout para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Adiciona diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

from nfse_search import NFSeDatabase, logger
from nuvem_fiscal_api import NuvemFiscalAPI

def buscar_nfse_teste():
    """Testa busca de NFS-e via Nuvem Fiscal."""
    print("\n" + "="*70)
    print("TESTE DE BUSCA REAL DE NFS-e VIA NUVEM FISCAL")
    print("="*70)
    
    try:
        # Inicializa banco
        db = NFSeDatabase()
        
        # Busca certificado com config de NFS-e
        certificados = db.get_certificados()
        
        cert_com_config = None
        for cert in certificados:
            cnpj, path, senha, informante, cuf = cert
            configs = db.get_config_nfse(cnpj)
            if configs:
                cert_com_config = cert
                config_nfse = configs[0]
                break
        
        if not cert_com_config:
            print("\n❌ Nenhum certificado com configuração de NFS-e encontrado")
            print("   Use test_nfse_module.py para configurar primeiro")
            return
        
        cnpj, cert_path, senha, informante, cuf = cert_com_config
        provedor, cod_municipio, insc_municipal, url = config_nfse
        
        print(f"\n✅ Certificado selecionado:")
        print(f"   CNPJ: {cnpj}")
        print(f"   Informante: {informante}")
        print(f"   Município: {cod_municipio}")
        print(f"   Provedor: {provedor}")
        
        # Verifica se usa Nuvem Fiscal
        if provedor != "NUVEMFISCAL":
            print(f"\n⚠️  Provedor '{provedor}' não é Nuvem Fiscal")
            print("   Este teste é específico para Nuvem Fiscal API")
            return
        
        print("\n📋 Inicializando Nuvem Fiscal API...")
        
        # Lê credenciais
        api_cred_path = Path(__file__).parent / "api_credentials.csv"
        with open(api_cred_path, 'r') as f:
            lines = f.readlines()
            if len(lines) < 2:
                print("❌ Arquivo de credenciais vazio")
                return
            
            # Header: Client ID,Client Secret
            # Dados: sQsof...,AftMV...
            client_id = lines[1].split(',')[0].strip()
            client_secret = lines[1].split(',')[1].strip()
        
        print(f"   Client ID: {client_id[:10]}...")
        
        # Inicializa API
        api = NuvemFiscalAPI(client_id, client_secret)
        
        print("\n🔍 Consultando NFS-e dos últimos 30 dias...")
        
        # Define período
        data_final = datetime.now()
        data_inicial = data_final - timedelta(days=30)
        
        print(f"   Período: {data_inicial.strftime('%Y-%m-%d')} até {data_final.strftime('%Y-%m-%d')}")
        print(f"   CNPJ Prestador: {cnpj}")
        
        # Faz consulta
        resultado = api.consultar_nfse(
            cnpj_prestador=cnpj,
            data_inicial=data_inicial.strftime('%Y-%m-%d'),
            data_final=data_final.strftime('%Y-%m-%d'),
            ambiente='homologacao'  # Começa em homologação
        )
        
        if resultado.get('sucesso'):
            notas = resultado.get('notas', [])
            print(f"\n✅ Consulta bem-sucedida!")
            print(f"   {len(notas)} nota(s) encontrada(s)")
            
            if notas:
                print("\n📋 Notas encontradas:\n")
                for idx, nota in enumerate(notas[:10], 1):  # Mostra primeiras 10
                    print(f"   {idx}. Número: {nota.get('numero')}")
                    print(f"      Data: {nota.get('data_emissao')}")
                    print(f"      Valor: R$ {nota.get('valor_servicos', 0):.2f}")
                    print(f"      Tomador: {nota.get('tomador', {}).get('razao_social', 'N/A')}")
                    print()
                
                if len(notas) > 10:
                    print(f"   ... e mais {len(notas) - 10} nota(s)")
            else:
                print("\n📭 Nenhuma nota encontrada no período")
                print("   Isso pode ser normal se:")
                print("   • Não houve emissão de NFS-e no período")
                print("   • Está em ambiente de homologação (dados de teste)")
                print("   • Município não usa Padrão Nacional")
        else:
            print(f"\n⚠️  Consulta retornou erro:")
            print(f"   {resultado.get('mensagem', 'Erro desconhecido')}")
            
            erro_detalhe = resultado.get('erro')
            if erro_detalhe:
                print(f"\n   Detalhes técnicos:")
                print(f"   {erro_detalhe}")
        
        return resultado
        
    except FileNotFoundError as e:
        print(f"\n❌ Arquivo não encontrado: {e}")
        print("   Verifique se api_credentials.csv existe")
    except Exception as e:
        print(f"\n❌ Erro durante a busca: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Executa teste de busca."""
    try:
        resultado = buscar_nfse_teste()
        
        print("\n" + "="*70)
        print("TESTE CONCLUÍDO")
        print("="*70)
        
        if resultado and resultado.get('sucesso'):
            print("\n✅ Integração com Nuvem Fiscal funcionando!")
            print("\n📚 Próximos passos:")
            print("   1. Verifique os dados retornados")
            print("   2. Teste em ambiente de produção (se necessário)")
            print("   3. Integre com a busca automática do sistema")
        else:
            print("\n⚠️  Teste não retornou sucesso")
            print("   Verifique:")
            print("   • Credenciais da API")
            print("   • Configuração do município")
            print("   • Se o município usa Padrão Nacional")
            print("   • Logs para mais detalhes")
        
        print()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
