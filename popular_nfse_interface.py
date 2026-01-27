# -*- coding: utf-8 -*-
"""
Script para popular a tabela notas_detalhadas com as NFS-e do banco nfe_data.db.
Isso fará as NFS-e aparecerem na interface principal (Busca NF-e.py).
"""

import sqlite3
from datetime import datetime
from lxml import etree

def popular_nfse_na_interface():
    """
    Migra NFS-e da tabela nfse_baixadas (nfe_data.db) para notas_detalhadas (notas.db).
    Assim as NFS-e aparecerão na interface junto com NF-e e CT-e.
    """
    
    print("🔄 Iniciando migração de NFS-e para interface...")
    
    # Conecta aos dois bancos
    conn_nfse = sqlite3.connect('nfe_data.db')
    conn_notas = sqlite3.connect('notas.db')
    
    try:
        # Busca todas NFS-e
        cursor_nfse = conn_nfse.execute('''
            SELECT numero_nfse, cnpj_prestador, cnpj_tomador, data_emissao, 
                   valor_servico, xml_content, data_download
            FROM nfse_baixadas
        ''')
        
        nfse_rows = cursor_nfse.fetchall()
        print(f"📊 Total de NFS-e encontradas: {len(nfse_rows)}")
        
        inseridas = 0
        atualizadas = 0
        
        for row in nfse_rows:
            numero_nfse, cnpj_prestador, cnpj_tomador, data_emissao, valor, xml_content, data_download = row
            
            try:
                # Parse do XML para extrair mais dados
                tree = etree.fromstring(xml_content.encode('utf-8'))
                ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}
                
                # Extrai dados do XML
                chave = tree.findtext('.//nfse:ChaveAcesso', namespaces=ns) or \
                        tree.findtext('.//ChaveAcesso') or \
                        f"NFSE_{numero_nfse}_{cnpj_prestador}"
                
                nome_prestador = tree.findtext('.//nfse:prest//nfse:xNome', namespaces=ns) or \
                                tree.findtext('.//prest//xNome') or \
                                tree.findtext('.//nfse:emit//nfse:xNome', namespaces=ns) or \
                                tree.findtext('.//emit//xNome') or \
                                'Não informado'
                
                nome_tomador = tree.findtext('.//nfse:toma//nfse:xNome', namespaces=ns) or \
                              tree.findtext('.//toma//xNome') or \
                              'Não informado'
                
                cod_municipio = tree.findtext('.//nfse:cMun', namespaces=ns) or \
                               tree.findtext('.//cMun') or \
                               tree.findtext('.//nfse:cLocEmi', namespaces=ns) or \
                               tree.findtext('.//cLocEmi') or \
                               ''
                
                # UF do município (primeiros 2 dígitos do código)
                uf = ''
                if cod_municipio and len(cod_municipio) >= 2:
                    codigo_uf = cod_municipio[:2]
                    ufs = {
                        '11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA',
                        '16': 'AP', '17': 'TO', '21': 'MA', '22': 'PI', '23': 'CE',
                        '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL', '28': 'SE',
                        '29': 'BA', '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP',
                        '41': 'PR', '42': 'SC', '43': 'RS', '50': 'MS', '51': 'MT',
                        '52': 'GO', '53': 'DF'
                    }
                    uf = ufs.get(codigo_uf, '')
                
                # Formata data para padrão YYYY-MM-DD
                try:
                    if 'T' in data_emissao:
                        data_formatada = data_emissao.split('T')[0]
                    else:
                        data_formatada = data_emissao[:10]
                except:
                    data_formatada = datetime.now().strftime('%Y-%m-%d')
                
                # Verifica se já existe
                existe = conn_notas.execute(
                    'SELECT COUNT(*) FROM notas_detalhadas WHERE chave = ?',
                    (chave,)
                ).fetchone()[0]
                
                # Insere ou atualiza
                conn_notas.execute('''
                    INSERT OR REPLACE INTO notas_detalhadas 
                    (chave, nome_emitente, cnpj_emitente, numero, data_emissao, tipo, 
                     valor, status, cnpj_destinatario, nome_destinatario, uf, 
                     xml_status, informante, atualizado_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chave,                          # chave única
                    nome_prestador,                 # nome_emitente (prestador)
                    cnpj_prestador,                 # cnpj_emitente (prestador)
                    numero_nfse,                    # numero
                    data_formatada,                 # data_emissao
                    'NFS-e',                        # tipo
                    str(valor),                     # valor
                    'AUTORIZADA',                   # status
                    cnpj_tomador,                   # cnpj_destinatario (tomador)
                    nome_tomador,                   # nome_destinatario (tomador)
                    uf,                             # uf
                    'COMPLETO',                     # xml_status
                    cnpj_prestador,                 # informante
                    datetime.now().isoformat()      # atualizado_em
                ))
                
                if existe:
                    atualizadas += 1
                else:
                    inseridas += 1
                
            except Exception as e:
                print(f"❌ Erro ao processar NFS-e {numero_nfse}: {e}")
                continue
        
        conn_notas.commit()
        
        print(f"\n✅ Migração concluída!")
        print(f"   📝 Novas NFS-e inseridas: {inseridas}")
        print(f"   🔄 NFS-e atualizadas: {atualizadas}")
        print(f"   📊 Total processado: {inseridas + atualizadas}")
        
        # Verifica resultado
        total_nfse = conn_notas.execute(
            "SELECT COUNT(*) FROM notas_detalhadas WHERE tipo = 'NFS-e'"
        ).fetchone()[0]
        
        print(f"\n📋 Total de NFS-e na interface: {total_nfse}")
        
        # Mostra amostra
        print("\n📄 Amostra das NFS-e (primeiras 5):")
        cursor = conn_notas.execute('''
            SELECT numero, nome_emitente, nome_destinatario, data_emissao, valor
            FROM notas_detalhadas 
            WHERE tipo = 'NFS-e'
            ORDER BY data_emissao DESC
            LIMIT 5
        ''')
        
        for row in cursor.fetchall():
            print(f"   • NFS-e {row[0]} | {row[1]} → {row[2]} | {row[3]} | R$ {row[4]}")
        
    finally:
        conn_nfse.close()
        conn_notas.close()


if __name__ == '__main__':
    popular_nfse_na_interface()
