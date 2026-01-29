#!/usr/bin/env python3
"""
Teste de manifestação usando PyNFe
"""
import sys
from pathlib import Path

# Adicionar diretório ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from modules.database import DatabaseManager
from pynfe.processamento.comunicacao import ComunicacaoSefaz
from pynfe.processamento.assinatura import AssinaturaA1
from pynfe.processamento.serializacao import SerializacaoXML
from pynfe.entidades.evento import EventoManifestacaoDest
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

def main():
    print("=" * 80)
    print("TESTE DE MANIFESTAÇÃO COM PyNFe")
    print("=" * 80)
    
    # Dados de teste - nota do teste anterior (nunca foi manifestada com sucesso)
    cnpj = "33251845000109"
    chave = "50251042263870000101550010009997851162320151"  # NF-e modelo 55 antiga
    
    # Carregar certificado
    print("\nBuscando certificado no banco de dados...")
    db_path = BASE_DIR / "notas.db"
    db = DatabaseManager(db_path)
    certs = db.load_certificates()
    
    cert_info = None
    for cert in certs:
        if cert.get('informante') == cnpj:
            cert_info = cert
            break
    
    if not cert_info:
        print(f"ERRO: Certificado não encontrado para CNPJ {cnpj}")
        return
    
    cert_path = cert_info['caminho']
    cert_senha = cert_info['senha']
    
    print(f"OK Certificado encontrado:")
    print(f"  Razao Social: {cert_info.get('razao_social', 'N/A')}")
    print(f"  CNPJ: {cert_info.get('cnpj_cpf')}")
    print(f"  Caminho: {cert_path}")
    
    if not Path(cert_path).exists():
        print(f"\nERRO: Arquivo do certificado não encontrado: {cert_path}")
        return
    
    print(f"\n{'=' * 80}")
    print("CRIANDO EVENTO DE MANIFESTAÇÃO")
    print(f"{'=' * 80}")
    print(f"Chave NF-e: {chave}")
    print(f"Tipo: Ciencia da Operacao (210210)")
    print(f"CNPJ destinatário: {cnpj}")
    
    try:
        # Criar evento de manifestação
        # operacao: 1=Confirmação, 2=Ciência, 3=Desconhecimento, 4=Operação não Realizada
        # IMPORTANTE: Para manifestação via AN, usar uf especial
        evento = EventoManifestacaoDest(
            cnpj=cnpj,
            chave=chave,
            data_emissao=datetime.now(),
            operacao=2,  # 2=Ciência da Operação
            uf='AN',  # AN = Ambiente Nacional para manifestação
            orgao='91',  # 91 = Ambiente Nacional
        )
        
        print(f"\nOK Evento criado")
        print(f"  Tipo: {evento.tp_evento}")
        print(f"  Descricao: {evento.descricao}")
        print(f"  Chave: {evento.chave}")
        print(f"  ID: {evento.identificador}")
        
        # Serializar evento para XML
        print(f"\nSerializando evento para XML...")
        serializador = SerializacaoXML(None, homologacao=False)  # False=Produção
        xml_evento_elem = serializador.serializar_evento(evento, retorna_string=False)
        
        # Converter para string
        from lxml import etree
        xml_str = etree.tostring(xml_evento_elem, encoding='unicode', pretty_print=True)
        print(f"OK XML do evento gerado ({len(xml_str)} bytes)")
        print(f"\nXML completo:")
        print(xml_str)  # XML completo para verificar cOrgao
        
        # Assinar evento
        print(f"\nAssinando evento...")
        assinatura = AssinaturaA1(cert_path, cert_senha)
        
        # Assinar o elemento XML
        xml_assinado_elem = assinatura.assinar(xml_evento_elem)
        
        # Converter para string
        xml_assinado_str = etree.tostring(xml_assinado_elem, encoding='unicode')
        print(f"OK Evento assinado ({len(xml_assinado_str)} bytes)")
        
        # Enviar para SEFAZ
        print(f"\nEnviando para SEFAZ...")
        comunicacao = ComunicacaoSefaz(
            uf='MS',
            certificado=cert_path,
            certificado_senha=cert_senha,
            homologacao=False  # False=Produção
        )
        
        # Enviar evento (manifestação é um tipo de evento)
        # modelo='55' para NF-e, evento=elemento XML assinado
        processo = comunicacao.evento(modelo='55', evento=xml_assinado_elem)
        
        print(f"\n{'=' * 80}")
        print("RESPOSTA SEFAZ:")
        print(f"{'=' * 80}")
        
        # A resposta é um objeto Response do requests
        print(f"Status HTTP: {processo.status_code}")
        print(f"Conteudo ({len(processo.text)} bytes):")
        print(processo.text)
        
        # Parsear XML da resposta
        from lxml import etree
        root = etree.fromstring(processo.content)
        
        # Extrair cStat e xMotivo
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        ret_env_evento = root.find('.//nfe:retEnvEvento', namespaces=ns)
        
        if ret_env_evento is not None:
            c_stat = ret_env_evento.findtext('.//nfe:cStat', namespaces=ns)
            x_motivo = ret_env_evento.findtext('.//nfe:xMotivo', namespaces=ns)
            
            print(f"\ncStat: {c_stat}")
            print(f"xMotivo: {x_motivo}")
            
            # Verificar retEvento
            ret_evento = ret_env_evento.find('.//nfe:retEvento', namespaces=ns)
            if ret_evento is not None:
                inf_evento = ret_evento.find('.//nfe:infEvento', namespaces=ns)
                if inf_evento is not None:
                    evento_c_stat = inf_evento.findtext('.//nfe:cStat', namespaces=ns)
                    evento_x_motivo = inf_evento.findtext('.//nfe:xMotivo', namespaces=ns)
                    evento_n_prot = inf_evento.findtext('.//nfe:nProt', namespaces=ns)
                    
                    print(f"\nEvento:")
                    print(f"  cStat: {evento_c_stat}")
                    print(f"  xMotivo: {evento_x_motivo}")
                    if evento_n_prot:
                        print(f"  Protocolo: {evento_n_prot}")
            
            if c_stat == '128':
                print("\nOK SUCESSO! Lote processado")
            
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
