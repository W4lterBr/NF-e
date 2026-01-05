#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para migrar pastas com nomenclatura antiga (certificado) para CNPJ
"""
import os
import sys
import sqlite3
from pathlib import Path
from lxml import etree

# Adicionar encoding UTF-8 no console Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Mapeamento pasta antiga -> CNPJ
# Formato: {"nome_pasta_antiga": "CNPJ_correto"}
# CNPJs obtidos da tabela certificados (informante)
MAPEAMENTO = {
    "75-PARTNESS FUTURA DIST": "47539664000197",
    "79-ALFA COMPUTADORES": "01773924000193",  
    "80-LUZ COMERCIO ALIMENT": "49068153000160",
    "99-JL COMERCIO": "48160135000140"
}

def extrair_cnpj_de_xml(xml_path: Path) -> str:
    """Extrai CNPJ do destinatário de um XML"""
    try:
        tree = etree.parse(str(xml_path))
        root = tree.getroot()
        
        # Namespace NFe/CTe
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        # Tentar pegar CNPJ do destinatário
        dest = root.find('.//nfe:dest', ns)
        if dest is not None:
            cnpj = dest.find('.//nfe:CNPJ', ns)
            if cnpj is not None and cnpj.text:
                return cnpj.text.strip()
        
        return None
    except Exception as e:
        print(f"[ERRO] Falha ao ler XML {xml_path.name}: {e}")
        return None

def detectar_cnpj_da_pasta(pasta_path: Path) -> str:
    """Detecta o CNPJ correto analisando XMLs da pasta"""
    cnpjs = {}
    
    # Pegar até 10 XMLs da pasta
    xmls = list(pasta_path.rglob("*.xml"))[:10]
    
    for xml_path in xmls:
        # Ignorar arquivos de sistema/debug
        if any(x in xml_path.name.lower() for x in ['debug', 'backup', 'request', 'response', 'protocolo', 'evento']):
            continue
            
        cnpj = extrair_cnpj_de_xml(xml_path)
        if cnpj:
            cnpjs[cnpj] = cnpjs.get(cnpj, 0) + 1
    
    # Retornar o CNPJ mais comum
    if cnpjs:
        return max(cnpjs, key=cnpjs.get)
    return None

def migrar_pasta(pasta_antiga: str, cnpj_destino: str, base_path: Path, dry_run: bool = False):
    """Migra uma pasta antiga para a nova estrutura de CNPJ"""
    pasta_origem = base_path / pasta_antiga
    pasta_destino = base_path / cnpj_destino
    
    if not pasta_origem.exists():
        print(f"[ERRO] Pasta {pasta_antiga} não encontrada")
        return
    
    print(f"\n{'='*80}")
    print(f"[INFO] Migrando: {pasta_antiga} -> {cnpj_destino}")
    print(f"{'='*80}")
    
    # Contar arquivos
    arquivos = list(pasta_origem.rglob("*.xml")) + list(pasta_origem.rglob("*.pdf"))
    total = len(arquivos)
    
    print(f"[INFO] Total de arquivos: {total}")
    
    if dry_run:
        print(f"[DRY-RUN] Seria movido de {pasta_origem} para {pasta_destino}")
        return
    
    # Criar pasta destino se não existe
    pasta_destino.mkdir(exist_ok=True)
    
    movidos = 0
    erros = 0
    
    for arquivo in arquivos:
        try:
            # Calcular caminho relativo dentro da pasta antiga
            caminho_relativo = arquivo.relative_to(pasta_origem)
            destino_arquivo = pasta_destino / caminho_relativo
            
            # Criar subpastas se necessário
            destino_arquivo.parent.mkdir(parents=True, exist_ok=True)
            
            # Mover arquivo
            arquivo.rename(destino_arquivo)
            movidos += 1
            
            if movidos % 100 == 0:
                print(f"[PROGRESS] {movidos}/{total} arquivos movidos...")
                
        except Exception as e:
            print(f"[ERRO] Falha ao mover {arquivo.name}: {e}")
            erros += 1
    
    print(f"\n[RESUMO] Movidos: {movidos}, Erros: {erros}")
    
    # Remover pasta antiga se vazia
    try:
        if not any(pasta_origem.rglob("*")):
            pasta_origem.rmdir()
            print(f"[OK] Pasta antiga {pasta_antiga} removida")
    except Exception as e:
        print(f"[AVISO] Não foi possível remover pasta antiga: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrar pastas antigas para estrutura de CNPJ")
    parser.add_argument("--dry-run", action="store_true", help="Simular sem mover arquivos")
    parser.add_argument("--auto-detect", action="store_true", help="Auto-detectar CNPJs dos XMLs")
    args = parser.parse_args()
    
    base_path = Path(__file__).parent / "xmls"
    
    print("[INFO] Iniciando migração de pastas antigas...")
    print(f"[INFO] Diretório base: {base_path}")
    
    # Se auto-detect, tentar descobrir CNPJs
    if args.auto_detect:
        print("\n[INFO] Modo auto-detect ativado")
        for pasta_antiga in MAPEAMENTO.keys():
            pasta_path = base_path / pasta_antiga
            if pasta_path.exists():
                cnpj = detectar_cnpj_da_pasta(pasta_path)
                if cnpj:
                    print(f"[DETECT] {pasta_antiga} -> CNPJ detectado: {cnpj}")
                    MAPEAMENTO[pasta_antiga] = cnpj
                else:
                    print(f"[AVISO] Não foi possível detectar CNPJ de {pasta_antiga}")
    
    # Migrar cada pasta
    for pasta_antiga, cnpj in MAPEAMENTO.items():
        migrar_pasta(pasta_antiga, cnpj, base_path, dry_run=args.dry_run)
    
    print("\n[CONCLUÍDO] Migração finalizada!")

if __name__ == "__main__":
    main()
