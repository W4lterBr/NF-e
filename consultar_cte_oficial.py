#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consulta CT-e usando URLs oficiais corrigidas
"""

import sys
import os

# Adiciona diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.database import DatabaseManager
from nfe_search import NFeService

def main():
    print("🔵 Consultando CT-e com código corrigido\n")
    print("="*80)
    
    # Chave a consultar
    chave = "50251203232675000154570010056290311009581385"
    uf = chave[:2]
    
    print(f"\n🔑 Chave: {chave}")
    print(f"📍 UF: {uf} (MS - Mato Grosso do Sul)\n")
    
    # Inicializa database
    db_path = os.path.join(os.path.dirname(__file__), "notas.db")
    db = DatabaseManager(db_path)
    
    # Carrega certificados
    certificados = db.load_certificates()
    if not certificados:
        print("❌ Nenhum certificado disponível")
        return
    
    print(f"📜 Certificados disponíveis: {len(certificados)}\n")
    
    # Inicializa searcher com primeiro certificado
    cert = certificados[0]
    searcher = NFeService(
        cert['caminho'], 
        cert['senha'],
        cert['cnpj_cpf'],
        uf
    )
    
    # Tenta consultar
    print("🔍 Consultando protocolo CT-e...\n")
    resultado = searcher.fetch_prot_cte(chave)
    
    if resultado:
        print("\n" + "="*80)
        print("✅ SUCESSO!")
        print("="*80)
        print(f"\n📄 XML retornado: {len(resultado)} bytes")
        
        # Extrai dados do evento
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(resultado)
            
            # Namespace
            ns = {
                'cte': 'http://www.portalfiscal.inf.br/cte',
                'ws': 'http://www.portalfiscal.inf.br/cte/wsdl/CTeConsultaV4'
            }
            
            # Extrai da resposta da consulta
            c_stat = root.findtext('.//cte:cStat', namespaces=ns) or root.findtext('.//cStat')
            x_motivo = root.findtext('.//cte:xMotivo', namespaces=ns) or root.findtext('.//xMotivo')
            
            print(f"\n📋 Resposta da Consulta:")
            print(f"   cStat: {c_stat}")
            print(f"   xMotivo: {x_motivo}")
            
            # Busca evento de cancelamento
            proc_evento = root.find('.//cte:procEventoCTe', namespaces=ns) or root.find('.//procEventoCTe')
            
            if proc_evento is not None:
                print("\n🎯 EVENTO DE CANCELAMENTO ENCONTRADO!")
                
                # Dados do evento
                tp_evento = proc_evento.findtext('.//cte:tpEvento', namespaces=ns) or proc_evento.findtext('.//tpEvento')
                dh_evento = proc_evento.findtext('.//cte:dhEvento', namespaces=ns) or proc_evento.findtext('.//dhEvento')
                x_just = proc_evento.findtext('.//cte:xJust', namespaces=ns) or proc_evento.findtext('.//xJust')
                n_prot_evento = proc_evento.findtext('.//cte:nProt', namespaces=ns) or proc_evento.findtext('.//nProt')
                
                # Dados do retorno do evento
                c_stat_evento = proc_evento.findtext('.//cte:retEventoCTe//cte:cStat', namespaces=ns) or proc_evento.findtext('.//retEventoCTe//cStat')
                dh_reg = proc_evento.findtext('.//cte:dhRegEvento', namespaces=ns) or proc_evento.findtext('.//dhRegEvento')
                
                print(f"\n📅 Detalhes do Evento:")
                print(f"   Tipo: {tp_evento} (110111 = Cancelamento)")
                print(f"   Data/Hora: {dh_evento}")
                print(f"   Justificativa: {x_just}")
                print(f"   Protocolo Evento: {n_prot_evento}")
                print(f"   Status Evento: {c_stat_evento} (135 = homologado)")
                print(f"   Data Registro: {dh_reg}")
                
                # Verifica se é cancelamento
                if tp_evento == '110111' and c_stat_evento == '135':
                    print("\n🎉 CANCELAMENTO CONFIRMADO!")
                    print("\n💾 Atualizando banco de dados...")
                    
                    novo_status = "Cancelamento de CT-e homologado"
                    db.atualizar_status_por_evento(chave, novo_status)
                    print(f"✅ Status atualizado para: {novo_status}")
                    
                    # Salva XML do evento
                    evento_xml = ET.tostring(proc_evento, encoding='unicode')
                    evento_path = f"evento_cancelamento_{chave}.xml"
                    with open(evento_path, 'w', encoding='utf-8') as f:
                        f.write(evento_xml)
                    print(f"📄 XML do evento salvo em: {evento_path}")
                else:
                    print(f"\n⚠️ Evento não é cancelamento ou não foi homologado")
            else:
                print("\n⚠️ Nenhum evento encontrado no XML")
                
        except Exception as e:
            print(f"\n❌ Erro ao processar XML: {e}")
            import traceback
            traceback.print_exc()
        
    else:
        print("\n" + "="*80)
        print("❌ SEM RESPOSTA")
        print("="*80)
    
    print("\n")

if __name__ == "__main__":
    main()
