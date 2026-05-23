"""
Script para importar CT-e das pastas para o banco de dados
"""

import sys
import io
from pathlib import Path
from modules.database import DatabaseManager
from lxml import etree

# Fix encoding para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Inicializa banco
db = DatabaseManager("nfe_system.db")

xmls_dir = Path("xmls")

print("\n" + "="*80)
print("IMPORTAÇÃO DE CT-e PARA O BANCO DE DADOS")
print("="*80 + "\n")

total_importados = 0
total_erros = 0
total_pulados = 0

for cnpj_folder in xmls_dir.iterdir():
    if not cnpj_folder.is_dir():
        continue
    if cnpj_folder.name in ['Debug de notas', 'COOPSERVIÇOS']:
        continue
    
    # Busca pastas de meses
    for mes_folder in cnpj_folder.iterdir():
        if not mes_folder.is_dir():
            continue
        
        # Busca pasta de CT-e
        cte_folder = mes_folder / "CTe"
        if not cte_folder.exists():
            continue
        
        # Processa cada XML
        for xml_file in cte_folder.glob("*.xml"):
            try:
                # Lê o XML
                tree = etree.parse(str(xml_file))
                root = tree.getroot()
                
                # Namespace do CT-e
                ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
                
                # Extrai dados
                infCte = root.find('.//cte:infCte', ns)
                if infCte is None:
                    print(f"Aviso: {xml_file.name} não é um CT-e válido")
                    total_erros += 1
                    continue
                
                chave = infCte.get('Id', '').replace('CTe', '')
                
                # Extrai dados do emitente
                emit = root.find('.//cte:emit', ns)
                cnpj_emit = emit.find('cte:CNPJ', ns).text if emit.find('cte:CNPJ', ns) is not None else ''
                nome_emit = emit.find('cte:xNome', ns).text if emit.find('cte:xNome', ns) is not None else ''
                
                # Extrai dados do destinatário
                dest = root.find('.//cte:dest', ns)
                cnpj_dest = dest.find('cte:CNPJ', ns).text if dest.find('cte:CNPJ', ns) is not None else ''
                if not cnpj_dest:
                    cnpj_dest = dest.find('cte:CPF', ns).text if dest.find('cte:CPF', ns) is not None else ''
                nome_dest = dest.find('cte:xNome', ns).text if dest.find('cte:xNome', ns) is not None else ''
                
                # Extrai outros dados
                ide = root.find('.//cte:ide', ns)
                numero = ide.find('cte:nCT', ns).text if ide.find('cte:nCT', ns) is not None else ''
                data_emissao = ide.find('cte:dhEmi', ns).text if ide.find('cte:dhEmi', ns) is not None else ''
                data_emissao = data_emissao[:10] if data_emissao else ''  # YYYY-MM-DD
                
                # Valor
                vPrest = root.find('.//cte:vPrest', ns)
                vTPrest_elem = vPrest.find('cte:vTPrest', ns) if vPrest is not None else None
                valor = float(vTPrest_elem.text) if vTPrest_elem is not None else 0.0
                
                # Status do protocolo
                protCTe = root.find('.//cte:protCTe', ns)
                if protCTe is not None:
                    xMotivo = protCTe.find('.//cte:xMotivo', ns)
                    status = xMotivo.text if xMotivo is not None else 'Autorizado'
                else:
                    status = 'Processado'
                
                # Salva no banco
                data = {
                    'chave': chave,
                    'cnpj_emitente': cnpj_emit,
                    'nome_emitente': nome_emit,
                    'cnpj_destinatario': cnpj_dest,
                    'nome_destinatario': nome_dest,
                    'numero': numero,
                    'data_emissao': data_emissao,
                    'tipo': 'CTe',
                    'valor': valor,
                    'status': status,
                    'informante': cnpj_folder.name.split('-')[0],  # CNPJ da pasta
                    'xml_status': 'COMPLETO',
                    'cfop': '',
                    'vencimento': None,
                    'ie_tomador': '',
                    'ncm': '',
                    'natureza': '',
                    'uf': '',
                    'base_icms': 0.0,
                    'valor_icms': 0.0
                }
                
                if db.save_note(data):
                    total_importados += 1
                    if total_importados % 50 == 0:
                        print(f"   Importados: {total_importados} CT-e...")
                else:
                    total_pulados += 1
                
            except Exception as e:
                total_erros += 1
                print(f"Erro em {xml_file.name}: {str(e)[:100]}")

print("\n" + "="*80)
print("RESUMO DA IMPORTAÇÃO:")
print("="*80)
print(f"OK Importados:  {total_importados:6d} CT-e")
print(f"-- Pulados:     {total_pulados:6d} CT-e (já existiam)")
print(f"XX Erros:       {total_erros:6d} CT-e")
print("\n")
