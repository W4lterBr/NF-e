"""
Script para testar diferentes combinações de URLs, namespaces e SOAPActions
para manifestação de CT-e no SVRS.
"""

import requests
from lxml import etree

# XML de evento assinado (exemplo)
xml_evento = """<evento xmlns="http://www.portalfiscal.inf.br/cte" versao="1.00">
<infEvento Id="ID6101105125125912625500014857001000073441100094856301">
<cOrgao>51</cOrgao>
<tpAmb>1</tpAmb>
<CNPJ>07606538000193</CNPJ>
<chCTe>51251259126255000148570010000734411000948563</chCTe>
<dhEvento>2026-01-05T19:00:00-03:00</dhEvento>
<tpEvento>610110</tpEvento>
<nSeqEvento>1</nSeqEvento>
<verEvento>1.00</verEvento>
<detEvento versao="1.00">
<descEvento>Prestacao do Servico em Desacordo</descEvento>
<xJust>MOTIVO - TRANSPORTADORA EMITIU ERRONEAMENTE.</xJust>
</detEvento>
</infEvento>
</evento>"""

# Combinações a testar
configuracoes = [
    {
        'nome': 'Versão 3 - CteRecepcaoEvento (case correto)',
        'url': 'https://cte.svrs.rs.gov.br/ws/CteRecepcaoEvento/CteRecepcaoEvento.asmx',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEvento',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEvento/cteRecepcaoEvento',
    },
    {
        'nome': 'Versão 4 - CteRecepcaoEventoV4',
        'url': 'https://cte.svrs.rs.gov.br/ws/CteRecepcaoEventoV4/CteRecepcaoEventoV4.asmx',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEventoV4',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEventoV4/cteRecepcaoEventoV4',
    },
    {
        'nome': 'Versão 4 - CTeRecepcaoEventoV4 (maiúscula)',
        'url': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoEventoV4',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4',
    },
    {
        'nome': 'Versão 3 - lowercase completo',
        'url': 'https://cte.svrs.rs.gov.br/ws/cterecepcaoevento/cterecepcaoevento.asmx',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/cterecepcaoevento',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/cterecepcaoevento/cterecepcaoevento',
    },
    {
        'nome': 'Versão 3 - namespace v3.00',
        'url': 'https://cte.svrs.rs.gov.br/ws/CteRecepcaoEvento/CteRecepcaoEvento.asmx',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEvento/3.00',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEvento/cteRecepcaoEvento',
    },
    {
        'nome': 'Versão 3 - SOAPAction sem operação',
        'url': 'https://cte.svrs.rs.gov.br/ws/CteRecepcaoEvento/CteRecepcaoEvento.asmx',
        'namespace': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEvento',
        'soap_action': 'http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEvento',
    },
]

def testar_configuracao(config):
    """Testa uma configuração específica"""
    print(f"\n{'='*80}")
    print(f"Testando: {config['nome']}")
    print(f"URL: {config['url']}")
    print(f"Namespace: {config['namespace']}")
    print(f"SOAPAction: {config['soap_action']}")
    print('='*80)
    
    # Monta SOAP envelope
    soap_envelope = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
<soap12:Body>
<cteDadosMsg xmlns="{config['namespace']}">{xml_evento}</cteDadosMsg>
</soap12:Body>
</soap12:Envelope>'''
    
    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
        'SOAPAction': f'"{config["soap_action"]}"',
    }
    
    try:
        response = requests.post(
            config['url'],
            data=soap_envelope.encode('utf-8'),
            headers=headers,
            verify=False,
            timeout=10
        )
        
        print(f"\n✓ Status HTTP: {response.status_code}")
        
        if response.status_code == 200:
            print("✓✓✓ SUCESSO! Esta configuração funciona! ✓✓✓")
            # Parse resposta
            try:
                root = etree.fromstring(response.content)
                print("\nResposta da SEFAZ:")
                print(etree.tostring(root, pretty_print=True, encoding='unicode'))
            except:
                print(response.text[:500])
            return True
            
        elif response.status_code == 404:
            print("✗ Erro 404 - URL não encontrada")
            
        elif response.status_code == 500:
            print("✗ Erro 500 - Possível problema no SOAP")
            # Tenta extrair mensagem de erro
            try:
                root = etree.fromstring(response.content)
                fault = root.find('.//{http://www.w3.org/2003/05/soap-envelope}Fault')
                if fault is not None:
                    reason = fault.find('.//{http://www.w3.org/2003/05/soap-envelope}Text')
                    if reason is not None:
                        print(f"  Mensagem: {reason.text}")
            except:
                pass
                
        else:
            print(f"✗ Status inesperado: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("✗ Timeout - Servidor não respondeu")
    except requests.exceptions.ConnectionError:
        print("✗ Erro de conexão")
    except Exception as e:
        print(f"✗ Erro: {e}")
    
    return False

if __name__ == '__main__':
    print("="*80)
    print("TESTE AUTOMATIZADO DE MANIFESTAÇÃO CT-e - SVRS")
    print("="*80)
    print("\nNOTA: Este teste usa um XML de exemplo SEM assinatura digital.")
    print("Esperamos erros de validação, mas podemos identificar a URL correta")
    print("se o erro NÃO for 404 ou 'invalid action'.\n")
    
    resultados = []
    for i, config in enumerate(configuracoes, 1):
        print(f"\n[{i}/{len(configuracoes)}]")
        sucesso = testar_configuracao(config)
        resultados.append((config['nome'], sucesso))
        
    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80)
    for nome, sucesso in resultados:
        status = "✓ FUNCIONOU" if sucesso else "✗ Falhou"
        print(f"{status}: {nome}")
    
    print("\n" + "="*80)
    print("Teste concluído!")
    print("="*80)
