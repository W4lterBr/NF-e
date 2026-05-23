#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 IMPORTAR XMLs DE UMA PASTA

Este script importa todos os XMLs de NF-e/CT-e encontrados em uma pasta
e subpastas, salvando os dados no banco.

Útil para:
- Importar NF-e de saída emitidas pela empresa
- Importar XMLs recebidos por email ou baixados manualmente
- Recuperar XMLs antigos para o banco de dados
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Adiciona diretório raiz ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from nfe_search import extrair_nota_detalhada, salvar_xml_por_certificado, XMLProcessor, DatabaseManager

# ============================================================================
# Configurações
# ============================================================================

DB_PATH = BASE_DIR / 'notas.db'


# ============================================================================
# Funções Auxiliares
# ============================================================================

def encontrar_xmls(pasta_raiz):
    """
    Busca recursivamente todos os arquivos XML em uma pasta.
    
    Args:
        pasta_raiz: Caminho da pasta raiz
    
    Returns:
        list: Lista de caminhos absolutos dos XMLs encontrados
    """
    pasta = Path(pasta_raiz)
    if not pasta.exists():
        return []
    
    xmls = []
    for arquivo in pasta.rglob('*.xml'):
        if arquivo.is_file():
            xmls.append(arquivo)
    
    return xmls


def identificar_tipo_xml(xml_content):
    """
    Identifica o tipo do XML.
    
    Returns:
        str: 'nfe', 'cte', 'cancelamento', 'evento', 'desconhecido'
    """
    if '<nfeProc' in xml_content or '<NFe' in xml_content:
        return 'nfe'
    elif '<procEventoNFe' in xml_content:
        if 'Cancelamento' in xml_content:
            return 'cancelamento'
        return 'evento'
    elif '<cteProc' in xml_content or '<CTe' in xml_content:
        return 'cte'
    else:
        return 'desconhecido'


def extrair_chave_xml(xml_content):
    """Extrai chave de acesso do XML."""
    import re
    
    # Tenta encontrar chave no XML
    patterns = [
        r'<chNFe>(\d{44})</chNFe>',
        r'chNFe>(\d{44})<',
        r'Id="NFe(\d{44})"',
        r'nfe_(\d{44})\.xml'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, xml_content)
        if match:
            return match.group(1)
    
    return None


# ============================================================================
# Função Principal
# ============================================================================

def main():
    """Função principal do script."""
    print()
    print("=" * 80)
    print("🚀 IMPORTAR XMLs DE PASTA")
    print("=" * 80)
    print()
    print("📌 Este script importa todos os XMLs de NF-e/CT-e de uma pasta.")
    print("   Os dados serão extraídos e salvos no banco de dados.")
    print()
    
    # Solicita pasta
    print("-" * 80)
    pasta_padrao = r"C:\Arquivo Walter - Empresas\Notas\79-ALFA COMPUTADORES"
    pasta = input(f"📁 Digite o caminho da pasta com os XMLs\n   (ENTER para usar: {pasta_padrao})\n> ").strip()
    
    if not pasta:
        pasta = pasta_padrao
    
    pasta_path = Path(pasta)
    
    if not pasta_path.exists():
        print()
        print(f"❌ ERRO: Pasta não encontrada: {pasta}")
        input("\nPressione ENTER para sair...")
        return
    
    print()
    print(f"✅ Pasta selecionada: {pasta_path}")
    print()
    print("🔍 Buscando arquivos XML...")
    
    # Busca XMLs
    xmls = encontrar_xmls(pasta_path)
    
    if not xmls:
        print()
        print("⚠️ Nenhum arquivo XML encontrado na pasta.")
        input("\nPressione ENTER para sair...")
        return
    
    print(f"✅ {len(xmls)} arquivo(s) XML encontrado(s)")
    print()
    
    # Confirma
    print("-" * 80)
    resposta = input(f"Deseja importar {len(xmls)} XML(s)? (S/N): ").strip().upper()
    if resposta not in ['S', 'SIM', 'Y', 'YES']:
        print("❌ Operação cancelada.")
        return
    
    print()
    print("=" * 80)
    print("🚀 INICIANDO IMPORTAÇÃO...")
    print("=" * 80)
    print()
    
    # Conecta ao banco
    db = DatabaseManager(DB_PATH)
    parser = XMLProcessor()
    
    # Estatísticas
    success = 0
    ja_existe = 0
    eventos = 0
    erros = 0
    erros_lista = []
    
    # Processa cada XML
    for idx, xml_file in enumerate(xmls, 1):
        print(f"[{idx}/{len(xmls)}] {xml_file.name}")
        
        try:
            # Lê XML
            with open(xml_file, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # Identifica tipo
            tipo = identificar_tipo_xml(xml_content)
            
            if tipo == 'desconhecido':
                print(f"  ⚠️ Tipo de XML não reconhecido, pulando...")
                erros += 1
                continue
            
            # Extrai chave
            chave = extrair_chave_xml(xml_content)
            
            if not chave:
                print(f"  ❌ Não foi possível extrair a chave de acesso")
                erros += 1
                erros_lista.append((xml_file.name, "Chave não encontrada"))
                continue
            
            print(f"  🔑 Chave: {chave}")
            print(f"  📋 Tipo: {tipo.upper()}")
            
            # Verifica se já existe
            with db._connect() as conn:
                cursor = conn.execute("SELECT numero, xml_status FROM notas_detalhadas WHERE chave = ?", (chave,))
                doc_existente = cursor.fetchone()
            
            if doc_existente:
                print(f"  ℹ️ Nota já existe no banco (Número: {doc_existente[0]}, Status: {doc_existente[1]})")
                ja_existe += 1
                print()
                continue
            
            # Se for evento, registra mas não cria registro principal
            if tipo in ['cancelamento', 'evento']:
                print(f"  📝 Evento detectado, salvando informação...")
                eventos += 1
                # TODO: Aqui poderia salvar evento em tabela específica
                print()
                continue
            
            # Extrai dados
            print(f"  📊 Extraindo dados...")
            
            # Determina informante (CNPJ da empresa)
            # Extrai CNPJ emitente do XML para determinar se é de saída
            if '<CNPJ>01773924000193</CNPJ>' in xml_content or 'ALFA COMPUTADORES' in xml_content:
                informante = '01773924000193'  # ALFA COMPUTADORES
            else:
                informante = '33251845000109'  # Usa certificado padrão
            
            nota_dados = extrair_nota_detalhada(
                xml_content,
                parser,
                db,
                chave,
                informante=informante,
                nsu_documento=""  # XMLs locais não têm NSU
            )
            
            # Salva no banco
            print(f"  💾 Salvando no banco...")
            db.salvar_nota_detalhada(nota_dados)
            
            # Registra XML (já tem caminho local)
            db.registrar_xml(chave, informante, str(xml_file))
            
            # Mostra informações
            num = nota_dados.get('numero', 'N/A')
            emit = nota_dados.get('nome_emitente', 'N/A')
            cnpj_emit = nota_dados.get('cnpj_emitente', 'N/A')
            valor = nota_dados.get('valor', 'N/A')
            
            print(f"  ✅ SUCESSO!")
            print(f"     • Número: {num}")
            print(f"     • Emitente: {emit}")
            print(f"     • CNPJ: {cnpj_emit}")
            print(f"     • Valor: R$ {valor}")
            
            # Identifica se é de saída
            if cnpj_emit and '01773924000193' in cnpj_emit:
                print(f"     • 📤 NF-e de SAÍDA (emitida pela ALFA)")
            else:
                print(f"     • 📥 NF-e de ENTRADA")
            
            success += 1
            
        except Exception as e:
            print(f"  ❌ ERRO: {e}")
            erros += 1
            erros_lista.append((xml_file.name, str(e)))
        
        print()
    
    # Relatório final
    print()
    print("=" * 80)
    print("📊 RELATÓRIO FINAL")
    print("=" * 80)
    print()
    print(f"✅ Importados com sucesso: {success}")
    print(f"ℹ️ Já existentes (pulados): {ja_existe}")
    print(f"📝 Eventos encontrados: {eventos}")
    print(f"❌ Erros: {erros}")
    print(f"📝 Total processado: {len(xmls)}")
    print()
    
    if erros_lista:
        print("-" * 80)
        print("❌ ERROS ENCONTRADOS:")
        print()
        for arquivo, erro in erros_lista[:10]:  # Mostra até 10 erros
            print(f"  • {arquivo}")
            print(f"    {erro}")
            print()
        
        if len(erros_lista) > 10:
            print(f"  ... e mais {len(erros_lista) - 10} erro(s)")
    
    if success > 0:
        print("-" * 80)
        print("✅ As notas importadas já estão disponíveis no sistema!")
        print("   📂 NF-e de SAÍDA → aba 'Emitidos pela empresa'")
        print("   📂 NF-e de ENTRADA → aba principal")
        print()
    
    input("Pressione ENTER para sair...")


# ============================================================================
# Ponto de Entrada
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Operação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n\n❌ ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        input("\nPressione ENTER para sair...")
