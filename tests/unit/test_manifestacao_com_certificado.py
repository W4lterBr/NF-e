"""
Script de teste para manifestação CT-e com certificado digital.
Testa múltiplas URLs do SVRS COM autenticação de certificado.
"""

import requests
from lxml import etree
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# XML de exemplo sem assinatura
evento_xml = """<?xml version="1.0" encoding="UTF-8"?>
<evento xmlns="http://www.portalfiscal.inf.br/cte" versao="1.00">
<infEvento>
<cOrgao>51</cOrgao>
<tpAmb>1</tpAmb>
<CNPJ>07606538000193</CNPJ>
<chCTe>51251259126255000148570010000734411000948563</chCTe>
<dhEvento>2026-01-05T19:30:09-03:00</dhEvento>
<tpEvento>610110</tpEvento>
<nSeqEvento>1</nSeqEvento>
<verEvento>1.00</verEvento>
<detEvento versao="1.00">
<descEvento>Prestacao do Servico em Desacordo</descEvento>
<xJust>MOTIVO - TESTE.</xJust>
</detEvento>
</infEvento>
</evento>"""

# Configurações de teste
configs = [
    {
        'nome': 'Versão 3 - CteRecepcaoEvento',
        'url': 'https://cte.svrs.rs.gov.br/ws/CteRecepcaoEvento/CteRecepcaoEvento.asmx',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEvento',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEvento/cteRecepcaoEvento'
    },
    {
        'nome': 'Versão 3 - sem .asmx',
        'url': 'https://cte.svrs.rs.gov.br/ws/CteRecepcaoEvento/CteRecepcaoEvento',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEvento',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEvento/cteRecepcaoEvento'
    },
    {
        'nome': 'Versão 3 - lowercase',
        'url': 'https://cte.svrs.rs.gov.br/ws/cterecepcaoevento/cterecepcaoevento.asmx',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/cterecepcaoevento',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/cterecepcaoevento/cterecepcaoevento'
    },
    {
        'nome': 'Versão 4 - CteRecepcaoEventoV4',
        'url': 'https://cte.svrs.rs.gov.br/ws/CteRecepcaoEventoV4/CteRecepcaoEventoV4.asmx',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEventoV4',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEventoV4/cteRecepcaoEventoV4'
    },
    {
        'nome': 'Versão 3 - CTeRecepcaoEvento (maiúscula)',
        'url': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEvento/CTeRecepcaoEvento.asmx',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoEvento',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoEvento/CTeRecepcaoEvento'
    },
    {
        'nome': 'URL alternativa 1 - cteRecepcaoEvento4',
        'url': 'https://cte.svrs.rs.gov.br/ws/cteRecepcaoEvento4/cteRecepcaoEvento4.asmx',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/cteRecepcaoEvento4',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/cteRecepcaoEvento4/cteRecepcaoEvento'
    },
    {
        'nome': 'URL alternativa 2 - CTeRecepcaoEvento4',
        'url': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEvento4/CTeRecepcaoEvento4.asmx',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoEvento4',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoEvento4/cteRecepcaoEvento'
    },
    {
        'nome': 'URL alternativa 3 - RecepcaoEventoCTe',
        'url': 'https://cte.svrs.rs.gov.br/ws/RecepcaoEventoCTe/RecepcaoEventoCTe.asmx',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/RecepcaoEventoCTe',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/RecepcaoEventoCTe/cteRecepcaoEvento'
    },
]

def testar_configuracao(config, cert_path=None, cert_password=None):
    """
    Testa uma configuração específica.
    
    Args:
        config: Dicionário com url, namespace e soap_action
        cert_path: Caminho do certificado .pfx (opcional)
        cert_password: Senha do certificado (opcional)
    """
    print(f"\n{'='*80}")
    print(f"Testando: {config['nome']}")
    print(f"URL: {config['url']}")
    print(f"Namespace: {config['namespace']}")
    print(f"SOAPAction: {config['soap_action']}")
    print(f"Certificado: {'SIM' if cert_path else 'NÃO'}")
    print('='*80)
    
    # Monta SOAP envelope
    soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
<soap12:Body>
<cteDadosMsg xmlns="{config['namespace']}">{evento_xml.replace('<?xml version="1.0" encoding="UTF-8"?>', '')}</cteDadosMsg>
</soap12:Body>
</soap12:Envelope>"""
    
    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
        'SOAPAction': f'"{config["soap_action"]}"'
    }
    
    try:
        # Prepara kwargs para requests
        request_kwargs = {
            'headers': headers,
            'data': soap_envelope.encode('utf-8'),
            'verify': False,
            'timeout': 10
        }
        
        # Adiciona certificado se fornecido
        if cert_path and cert_password:
            try:
                # Converte .pfx para formato requests (precisa de requests_pkcs12)
                from requests_pkcs12 import Pkcs12Adapter
                session = requests.Session()
                session.mount('https://', Pkcs12Adapter(
                    pkcs12_filename=cert_path,
                    pkcs12_password=cert_password
                ))
                response = session.post(config['url'], **request_kwargs)
            except ImportError:
                print("⚠️  requests_pkcs12 não disponível, tentando sem certificado...")
                response = requests.post(config['url'], **request_kwargs)
        else:
            response = requests.post(config['url'], **request_kwargs)
        
        print(f"✓ Status HTTP: {response.status_code}")
        
        # Analisa resposta
        if response.status_code == 200:
            print("✓ SUCESSO! Esta URL funciona!")
            # Tenta parsear XML de resposta
            try:
                root = etree.fromstring(response.content)
                print(f"✓ Resposta XML válida recebida")
                # Procura por cStat
                ns = {'soap': 'http://www.w3.org/2003/05/soap-envelope'}
                body = root.find('.//soap:Body', ns)
                if body is not None:
                    print(f"✓ SOAP Body encontrado")
            except Exception as e:
                print(f"⚠️  Erro ao parsear resposta: {e}")
        elif response.status_code == 403:
            print("⚠️  Status 403 - Provavelmente precisa de certificado válido")
        elif response.status_code == 404:
            print("✗ Status 404 - URL não existe neste servidor")
        elif response.status_code == 500:
            print("⚠️  Status 500 - Erro interno do servidor")
            # Tenta extrair mensagem de erro SOAP
            try:
                root = etree.fromstring(response.content)
                fault = root.find('.//{http://www.w3.org/2003/05/soap-envelope}Fault')
                if fault is not None:
                    reason = fault.find('.//{http://www.w3.org/2003/05/soap-envelope}Text')
                    if reason is not None:
                        print(f"   Mensagem: {reason.text}")
            except:
                pass
        else:
            print(f"✗ Status inesperado: {response.status_code}")
            
        return {
            'config': config['nome'],
            'status': response.status_code,
            'success': response.status_code == 200
        }
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Erro de conexão: {e}")
        return {
            'config': config['nome'],
            'status': 'ERRO',
            'success': False
        }

def main():
    print("="*80)
    print("TESTE AUTOMATIZADO DE MANIFESTAÇÃO CT-e - SVRS")
    print("TESTANDO COM E SEM CERTIFICADO DIGITAL")
    print("="*80)
    
    # Pergunta se quer testar com certificado
    print("\n🔐 Certificado Digital:")
    print("1. Testar SEM certificado (apenas validar URLs)")
    print("2. Testar COM certificado (requer .pfx e senha)")
    escolha = input("\nEscolha (1 ou 2): ").strip()
    
    cert_path = None
    cert_password = None
    
    if escolha == '2':
        cert_path = input("Caminho do certificado .pfx: ").strip().strip('"')
        cert_password = input("Senha do certificado: ").strip()
        print(f"\n✓ Usando certificado: {cert_path}")
    else:
        print("\n⚠️  Testando sem certificado (esperamos 403 para URLs válidas)")
    
    print(f"\n🔍 Testando {len(configs)} configurações diferentes...\n")
    
    resultados = []
    for i, config in enumerate(configs, 1):
        print(f"\n[{i}/{len(configs)}]")
        resultado = testar_configuracao(config, cert_path, cert_password)
        resultados.append(resultado)
    
    # Resumo
    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80)
    
    sucessos = [r for r in resultados if r['success']]
    http_403 = [r for r in resultados if r['status'] == 403]
    http_404 = [r for r in resultados if r['status'] == 404]
    http_500 = [r for r in resultados if r['status'] == 500]
    
    if sucessos:
        print("\n✓ CONFIGURAÇÕES QUE FUNCIONARAM:")
        for r in sucessos:
            print(f"  • {r['config']}")
    
    if http_403:
        print("\n⚠️  URLs VÁLIDAS (precisam de certificado válido) - HTTP 403:")
        for r in http_403:
            print(f"  • {r['config']}")
    
    if http_404:
        print("\n✗ URLs INEXISTENTES - HTTP 404:")
        for r in http_404:
            print(f"  • {r['config']}")
    
    if http_500:
        print("\n⚠️  ERRO NO SERVIDOR - HTTP 500:")
        for r in http_500:
            print(f"  • {r['config']}")
    
    print("\n" + "="*80)
    print("Teste concluído!")
    print("="*80)
    
    # Recomendação
    print("\n💡 INTERPRETAÇÃO DOS RESULTADOS:")
    print("  • HTTP 200: URL correta e funcionando!")
    print("  • HTTP 403: URL existe, mas precisa de certificado válido/autorizado")
    print("  • HTTP 404: URL não existe neste servidor")
    print("  • HTTP 500: Erro no servidor (problema com SOAP/namespace)")

if __name__ == '__main__':
    main()
