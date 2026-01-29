#!/usr/bin/env python3
"""Teste simples de consulta CT-e direto no SVRS."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from nfe_search import NFeService, DatabaseManager

CHAVE_CTE = "50251203232675000154570010056290311009581385"

def main():
    print(f"\n{'='*80}")
    print("TESTE CONSULTA CT-e DIRETO SVRS")
    print(f"{'='*80}\n")
    
    db_path = BASE_DIR / "notas_test.db"
    db = DatabaseManager(db_path)
    
    certificados = db.get_certificados()
    if not certificados:
        print("❌ Nenhum certificado!")
        return
    
    # Pega primeiro certificado
    cnpj, path, senha, inf, cuf = certificados[0]
    print(f"Certificado: {cnpj} ({inf})\n")
    
    try:
        svc = NFeService(path, senha, cnpj, cuf)
        
        # Força URL do SVRS
        url_svrs = "https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx"
        
        print(f"URL SVRS: {url_svrs}")
        print(f"Chave: {CHAVE_CTE}\n")
        
        # Monta XML de consulta
        xml_consulta = f'''<consSitCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="4.00">
    <tpAmb>1</tpAmb>
    <xServ>CONSULTAR</xServ>
    <chCTe>{CHAVE_CTE}</chCTe>
</consSitCTe>'''
        
        # Envelope SOAP 1.2 (SEM barra final no namespace)
        soap_envelope = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap12:Body>
    <cteDadosMsg xmlns="http://www.portalfiscal.inf.br/cte/wsdl/CteConsultaV4">{xml_consulta}</cteDadosMsg>
  </soap12:Body>
</soap12:Envelope>'''
        
        print("Enviando consulta...\n")
        
        headers = {
            'Content-Type': 'application/soap+xml; charset=utf-8',
        }
        
        resp = svc.dist_client.transport.session.post(url_svrs, data=soap_envelope.encode('utf-8'), headers=headers, timeout=30)
        
        print(f"Status Code: {resp.status_code}")
        print(f"Tamanho resposta: {len(resp.content)} bytes\n")
        
        if resp.status_code == 200:
            print("✅ SUCESSO!\n")
            content = resp.content.decode('utf-8')
            print(content[:2000])
            print("\n...")
            
            # Salva resposta
            output = BASE_DIR / f"{CHAVE_CTE}_consulta_svrs.xml"
            with open(output, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"\n📄 Resposta salva: {output}")
        else:
            print(f"❌ Erro {resp.status_code}\n")
            print(resp.content.decode('utf-8')[:1000])
            
    except Exception as e:
        print(f"❌ Exceção: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
