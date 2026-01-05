#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Buscar evento específico de CT-e via distribuição
"""

import sys
import sqlite3
from pathlib import Path
from lxml import etree
from datetime import datetime

# Adicionar path dos módulos
sys.path.insert(0, str(Path(__file__).parent))

from nfe_search import NFeService, DatabaseManager

CHAVE_CTE = '50251203232675000154570010056290311009581385'
INFORMANTE_CNPJ = '01773924000193'

def main():
    print("="*80)
    print("BUSCAR EVENTO DE CT-e VIA DISTRIBUIÇÃO")
    print("="*80)
    print(f"Chave CT-e: {CHAVE_CTE}")
    print(f"Informante: {INFORMANTE_CNPJ}\n")
    
    # Verificar status atual
    db = DatabaseManager('notas.db')
    conn = sqlite3.connect('notas.db')
    cursor = conn.execute(
        "SELECT numero, status FROM notas_detalhadas WHERE chave = ?",
        (CHAVE_CTE,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        print(f"📋 Status ATUAL no banco:")
        print(f"   Número: {row[0]}")
        print(f"   Status: {row[1]}\n")
    else:
        print("❌ CT-e não encontrado no banco\n")
        return
    
    # Carregar certificado (usando método do DB que descriptografa)
    certificados = db.get_certificados()
    cert_row = None
    
    for cert in certificados:
        if cert[0] == INFORMANTE_CNPJ:  # cnpj_cpf
            cert_row = cert
            break
    
    if not cert_row:
        print(f"❌ Certificado não encontrado para {INFORMANTE_CNPJ}")
        return
    
    cert_cnpj, cert_path, cert_senha, informante, cuf = cert_row
    print(f"✅ Certificado encontrado:")
    print(f"   CNPJ: {cert_cnpj}")
    print(f"   UF: {cuf}")
    print(f"   Caminho: {cert_path}\n")
    
    # Criar serviço
    nfe_service = NFeService(
        cert_path=cert_path,
        senha=cert_senha,
        informante=cert_cnpj,
        cuf=cuf
    )
    
    print("🔍 Buscando eventos via distribuição por CHAVE...\n")
    
    try:
        # Consultar distribuição pela chave específica
        resultado = nfe_service.consultar_distribuicao_chave(
            cnpj=INFORMANTE_CNPJ,
            chave=CHAVE_CTE
        )
        
        if not resultado:
            print("❌ Nenhum resultado da distribuição")
            return
        
        # Parsear resposta
        if isinstance(resultado, str):
            root = etree.fromstring(resultado.encode('utf-8'))
        else:
            root = etree.fromstring(resultado)
        
        # Namespace
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        # Buscar status
        c_stat = root.findtext('.//nfe:cStat', namespaces=ns)
        x_motivo = root.findtext('.//nfe:xMotivo', namespaces=ns)
        
        print(f"📊 Resposta da SEFAZ:")
        print(f"   cStat: {c_stat}")
        print(f"   Motivo: {x_motivo}\n")
        
        if c_stat != '138':
            print(f"⚠️ Status inesperado: {c_stat} - {x_motivo}")
            return
        
        # Buscar documentos
        docs = root.findall('.//nfe:docZip', namespaces=ns)
        print(f"📦 Documentos encontrados: {len(docs)}\n")
        
        eventos_encontrados = 0
        
        for doc in docs:
            schema = doc.get('schema')
            conteudo_b64 = doc.text
            
            if not conteudo_b64:
                continue
            
            # Decodificar
            import base64
            import gzip
            
            conteudo_zip = base64.b64decode(conteudo_b64)
            conteudo_xml = gzip.decompress(conteudo_zip)
            
            # Parsear XML
            doc_root = etree.fromstring(conteudo_xml)
            doc_tag = doc_root.tag.split('}')[-1] if '}' in doc_root.tag else doc_root.tag
            
            print(f"   📄 Schema: {schema}, Tag: {doc_tag}")
            
            # Se for evento de CT-e
            if doc_tag in ['procEventoCTe', 'eventoCTe']:
                eventos_encontrados += 1
                
                # Extrair dados do evento
                ns_cte = {'cte': 'http://www.portalfiscal.inf.br/cte'}
                
                ch_cte = doc_root.findtext('.//cte:chCTe', namespaces=ns_cte)
                tp_evento = doc_root.findtext('.//cte:tpEvento', namespaces=ns_cte)
                c_stat_ev = doc_root.findtext('.//cte:cStat', namespaces=ns_cte)
                x_evento = doc_root.findtext('.//cte:xEvento', namespaces=ns_cte)
                dh_reg_evento = doc_root.findtext('.//cte:dhRegEvento', namespaces=ns_cte)
                
                print(f"\n   🎯 EVENTO DE CT-e ENCONTRADO!")
                print(f"      Chave: {ch_cte}")
                print(f"      Tipo Evento: {tp_evento}")
                print(f"      Status: {c_stat_ev}")
                print(f"      Descrição: {x_evento}")
                print(f"      Data/Hora: {dh_reg_evento}")
                
                # Verificar se é cancelamento
                if tp_evento == '110111' and c_stat_ev == '135':
                    print(f"\n   🚫 CANCELAMENTO DETECTADO!")
                    
                    # Salvar XML do evento
                    eventos_dir = Path('xmls') / INFORMANTE_CNPJ / '2025-12' / 'Eventos'
                    eventos_dir.mkdir(parents=True, exist_ok=True)
                    
                    evento_file = eventos_dir / f"{CHAVE_CTE}-CANCELAMENTO.xml"
                    evento_file.write_bytes(conteudo_xml)
                    print(f"   💾 Evento salvo em: {evento_file}")
                    
                    # Atualizar status no banco
                    novo_status = "Cancelamento de CT-e homologado"
                    db.atualizar_status_por_evento(CHAVE_CTE, novo_status)
                    print(f"   ✅ Status atualizado para: {novo_status}")
                    
        print(f"\n{'='*80}")
        print(f"📊 RESUMO:")
        print(f"   Eventos de CT-e encontrados: {eventos_encontrados}")
        
        # Verificar status final
        conn = sqlite3.connect('notas.db')
        cursor = conn.execute(
            "SELECT status FROM notas_detalhadas WHERE chave = ?",
            (CHAVE_CTE,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            print(f"   Status FINAL no banco: {row[0]}")
        
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Erro ao buscar evento: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
