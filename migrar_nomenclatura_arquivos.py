"""
Script de Migração - Renomeia arquivos antigos para o novo padrão

⚠️ PADRÃO v1.0.86:
- Arquivo antigo: {numero}-{nome}.xml
- Arquivo novo: {chave}.xml

Este script:
1. Busca todos os XMLs na pasta xmls/
2. Extrai a chave de cada XML
3. Renomeia para {chave}.xml
4. Atualiza o banco de dados xmls_baixados
5. Gera relatório detalhado

USO:
    python migrar_nomenclatura_arquivos.py [--dry-run] [--pasta PASTA]

OPÇÕES:
    --dry-run       Apenas simula (não renomeia nada)
    --pasta PASTA   Pasta específica para migrar (padrão: xmls/)
    --verbose       Mostra todos os detalhes

EXEMPLOS:
    # Simular migração (seguro):
    python migrar_nomenclatura_arquivos.py --dry-run
    
    # Executar migração real:
    python migrar_nomenclatura_arquivos.py
    
    # Migrar pasta específica:
    python migrar_nomenclatura_arquivos.py --pasta "xmls/47539664000197"
"""

import os
import sys
import sqlite3
from pathlib import Path
from lxml import etree
import argparse
from datetime import datetime

def extrair_chave_do_xml(xml_path):
    """Extrai a chave de acesso de um arquivo XML."""
    try:
        # Lê o arquivo completo (arquivos XML raramente são muito grandes)
        with open(xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        root = etree.fromstring(content.encode('utf-8'))
        root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        
        # NFe
        if root_tag in ['nfeProc', 'NFe']:
            ns = '{http://www.portalfiscal.inf.br/nfe}'
            infNFe = root.find(f'.//{ns}infNFe')
            if infNFe is not None:
                chave_id = infNFe.attrib.get('Id', '')
                if chave_id:
                    chave = chave_id.replace('NFe', '')[-44:]
                    return chave if len(chave) == 44 else None
        
        # CTe
        elif root_tag in ['cteProc', 'CTe']:
            ns = '{http://www.portalfiscal.inf.br/cte}'
            infCte = root.find(f'.//{ns}infCte')
            if infCte is not None:
                chave_id = infCte.attrib.get('Id', '')
                if chave_id:
                    chave = chave_id.replace('CTe', '')[-44:]
                    return chave if len(chave) == 44 else None
        
        # Resumo NFe
        elif root_tag == 'resNFe':
            ns = '{http://www.portalfiscal.inf.br/nfe}'
            chave = root.findtext(f'{ns}chNFe')
            return chave if chave and len(chave) == 44 else None
        
        # Eventos
        elif root_tag in ['resEvento', 'procEventoNFe', 'evento', 'retEvento']:
            ns = '{http://www.portalfiscal.inf.br/nfe}'
            chave = root.findtext(f'.//{ns}chNFe')
            return chave if chave and len(chave) == 44 else None
        
        return None
    except Exception as e:
        print(f"      ❌ Erro ao parsear XML: {e}")
        return None

def migrar_arquivo(xml_path, dry_run=False, verbose=False):
    """
    Migra um arquivo individual.
    Retorna: (success, old_name, new_name, chave)
    """
    # Ignora pastas de debug
    if 'Debug de notas' in str(xml_path) or 'debug' in xml_path.name.lower():
        if verbose:
            print(f"    ⏭️  Arquivo de debug ignorado: {xml_path.name}")
        return (True, xml_path.name, None, None)
    
    # Ignora arquivos que já estão no padrão correto (nome = 44 dígitos + .xml)
    nome_arquivo = xml_path.name
    nome_sem_ext = nome_arquivo.replace('.xml', '')
    if nome_sem_ext.isdigit() and len(nome_sem_ext) == 44:
        if verbose:
            print(f"    ⏭️  Já está no padrão: {nome_arquivo}")
        return (True, nome_arquivo, nome_arquivo, nome_sem_ext)
    
    # Ignora arquivos de sistema (request/response/protocolo)
    if any(x in nome_arquivo.lower() for x in ['request', 'response', 'protocolo']):
        if verbose:
            print(f"    ⏭️  Arquivo de sistema ignorado: {nome_arquivo}")
        return (True, nome_arquivo, None, None)
    
    print(f"    📄 Processando: {nome_arquivo}")
    
    # Extrai chave do XML
    chave = extrair_chave_do_xml(xml_path)
    if not chave:
        print(f"      ⚠️  Não foi possível extrair chave válida")
        return (False, nome_arquivo, None, None)
    
    # Define novo nome
    novo_nome = f"{chave}.xml"
    novo_caminho = xml_path.parent / novo_nome
    
    # Verifica se arquivo destino já existe
    if novo_caminho.exists() and novo_caminho != xml_path:
        print(f"      ⚠️  Arquivo destino já existe: {novo_nome}")
        return (False, nome_arquivo, novo_nome, chave)
    
    # Verifica PDF correspondente
    pdf_path = xml_path.with_suffix('.pdf')
    pdf_exists = pdf_path.exists()
    
    if dry_run:
        print(f"      🔄 [DRY-RUN] Renomearia: {nome_arquivo} → {novo_nome}")
        if pdf_exists:
            print(f"      🔄 [DRY-RUN] Renomearia PDF também")
    else:
        try:
            # Renomeia XML
            xml_path.rename(novo_caminho)
            print(f"      ✅ Renomeado: {nome_arquivo} → {novo_nome}")
            
            # Renomeia PDF se existir
            if pdf_exists:
                novo_pdf = novo_caminho.with_suffix('.pdf')
                pdf_path.rename(novo_pdf)
                print(f"      ✅ PDF renomeado também")
        except Exception as e:
            print(f"      ❌ Erro ao renomear: {e}")
            return (False, nome_arquivo, novo_nome, chave)
    
    return (True, nome_arquivo, novo_nome, chave)

def atualizar_banco_dados(chave, novo_caminho, dry_run=False):
    """Atualiza o caminho no banco de dados."""
    if dry_run:
        return True
    
    try:
        db_path = Path(__file__).parent / 'notas_test.db'
        if not db_path.exists():
            return False
        
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute('''
                UPDATE xmls_baixados 
                SET caminho_arquivo = ?
                WHERE chave = ?
            ''', (str(novo_caminho.absolute()), chave))
            conn.commit()
        return True
    except Exception:
        return False

def migrar_pasta(pasta_base, dry_run=False, verbose=False):
    """Migra todos os XMLs de uma pasta recursivamente."""
    pasta = Path(pasta_base)
    
    if not pasta.exists():
        print(f"❌ Pasta não existe: {pasta}")
        return
    
    print(f"\n{'='*60}")
    print(f"🔄 MIGRAÇÃO DE ARQUIVOS - {'DRY RUN' if dry_run else 'MODO REAL'}")
    print(f"{'='*60}")
    print(f"📁 Pasta: {pasta}")
    print(f"⏰ Início: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    # Lista todos os XMLs (excluindo pastas de debug)
    print(f"📊 Escaneando arquivos XML...\n")
    xml_files = []
    for xml_file in pasta.rglob("*.xml"):
        # Ignora pastas de debug e sistema
        if any(x in str(xml_file) for x in ['Debug de notas', '\\debug\\', '/debug/']):
            continue
        if any(x in xml_file.name.lower() for x in ['debug', 'request', 'response', 'protocolo']):
            continue
        xml_files.append(xml_file)
    
    total = len(xml_files)
    
    print(f"📊 Total de XMLs encontrados: {total}")
    print()
    
    # Estatísticas
    stats = {
        'sucesso': 0,
        'erro': 0,
        'ja_padrao': 0,
        'ignorado': 0,
        'banco_atualizado': 0
    }
    
    migrados = []
    
    # Processa cada arquivo
    for idx, xml_path in enumerate(xml_files, 1):
        print(f"  [{idx}/{total}] {xml_path.relative_to(pasta)}")
        
        success, old_name, new_name, chave = migrar_arquivo(xml_path, dry_run, verbose)
        
        if success:
            if new_name and new_name != old_name:
                stats['sucesso'] += 1
                migrados.append({
                    'old': old_name,
                    'new': new_name,
                    'chave': chave,
                    'path': xml_path.parent
                })
                
                # Atualiza banco de dados
                if chave:
                    novo_caminho = xml_path.parent / new_name
                    if atualizar_banco_dados(chave, novo_caminho, dry_run):
                        stats['banco_atualizado'] += 1
                        if verbose:
                            print(f"      💾 Banco atualizado")
            elif new_name == old_name:
                stats['ja_padrao'] += 1
            else:
                stats['ignorado'] += 1
        else:
            stats['erro'] += 1
        
        print()
    
    # Relatório final
    print(f"\n{'='*60}")
    print(f"📊 RELATÓRIO FINAL")
    print(f"{'='*60}")
    print(f"✅ Migrados com sucesso: {stats['sucesso']}")
    print(f"⏭️  Já no padrão correto: {stats['ja_padrao']}")
    print(f"⏭️  Ignorados (sistema): {stats['ignorado']}")
    print(f"❌ Erros: {stats['erro']}")
    print(f"💾 Banco atualizado: {stats['banco_atualizado']}")
    print(f"📊 Total processado: {total}")
    print(f"⏰ Fim: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    # Lista arquivos migrados
    if migrados and not dry_run:
        print(f"\n📋 ARQUIVOS MIGRADOS:")
        for item in migrados[:20]:  # Mostra até 20
            print(f"  ✅ {item['old']} → {item['new']}")
        if len(migrados) > 20:
            print(f"  ... e mais {len(migrados) - 20} arquivos")
    
    if dry_run:
        print(f"\n⚠️  DRY RUN: Nenhum arquivo foi realmente renomeado")
        print(f"Execute sem --dry-run para aplicar as mudanças")

def main():
    parser = argparse.ArgumentParser(
        description='Migra arquivos XML para o novo padrão de nomenclatura (v1.0.86)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simula a migração sem renomear arquivos'
    )
    parser.add_argument(
        '--pasta',
        type=str,
        default='xmls',
        help='Pasta para migrar (padrão: xmls/)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Mostra todos os detalhes'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("  MIGRACAO DE NOMENCLATURA DE ARQUIVOS - v1.0.86")
    print("="*60)
    print("  Padrao Antigo: {numero}-{nome}.xml")
    print("  Padrao Novo:   {chave}.xml (44 digitos)")
    print("="*60)
    print()
    
    if args.dry_run:
        print("[!] MODO DRY RUN: Apenas simulacao, nenhum arquivo sera modificado\n")
    else:
        print("[!] MODO REAL: Arquivos serao renomeados!\n")
        resposta = input("Deseja continuar? (s/N): ")
        if resposta.lower() not in ['s', 'sim', 'yes', 'y']:
            print("[X] Operacao cancelada pelo usuario")
            return
    
    migrar_pasta(args.pasta, args.dry_run, args.verbose)

if __name__ == '__main__':
    main()
