"""
Script para reorganizar eventos da pasta 'desconhecido' para as pastas corretas.

Extrai o CNPJ da chave de acesso (posições 6-20) e move os arquivos para:
xmls/{CNPJ}/{ANO-MES}/Eventos/{CHAVE}.xml

IMPORTANTE: Executa em modo SEGURO (copia + verifica + deleta)
"""

import os
import shutil
from pathlib import Path
from lxml import etree

def extrair_cnpj_da_chave(chave: str) -> str:
    """
    Extrai CNPJ da chave de acesso (44 dígitos).
    Posições 6-20: CNPJ do emitente (14 dígitos)
    
    Exemplo: 50251233251845000109550010000294201523072059
             ^^^^^^^^^^^^^^ <- CNPJ: 33251845000109
    """
    if len(chave) >= 20:
        return chave[6:20]
    return None

def reorganizar_eventos(pasta_storage: str = None):
    """
    Reorganiza eventos da pasta 'desconhecido' para as pastas corretas.
    
    Args:
        pasta_storage: Caminho da pasta de armazenamento (ex: 'c:\\Arquivo Walter\\...\\NFs')
                      Se None, usa apenas a pasta local 'xmls'
    """
    pastas_para_verificar = []
    
    # 1. Pasta local (xmls/desconhecido)
    pasta_local = Path('xmls') / 'desconhecido'
    if pasta_local.exists():
        pastas_para_verificar.append(('LOCAL', pasta_local))
    
    # 2. Pasta de armazenamento (storage)
    if pasta_storage:
        pasta_storage_path = Path(pasta_storage) / 'desconhecido'
        if pasta_storage_path.exists():
            pastas_para_verificar.append(('STORAGE', pasta_storage_path))
    
    if not pastas_para_verificar:
        print("❌ Nenhuma pasta 'desconhecido' encontrada")
        return
    
    total_movidos = 0
    total_erros = 0
    
    for tipo_pasta, pasta_desconhecido in pastas_para_verificar:
        print(f"\n{'='*60}")
        print(f"📂 Processando pasta {tipo_pasta}: {pasta_desconhecido}")
        print(f"{'='*60}\n")
        
        # Busca todos os arquivos XML recursivamente
        arquivos_xml = list(pasta_desconhecido.rglob('*.xml'))
        print(f"📄 Encontrados {len(arquivos_xml)} arquivos XML\n")
        
        for idx, arquivo_xml in enumerate(arquivos_xml, 1):
            try:
                # Extrai chave do nome do arquivo
                chave = arquivo_xml.stem  # Remove .xml
                
                # Valida chave (44 dígitos)
                if not chave.isdigit() or len(chave) != 44:
                    print(f"[{idx}/{len(arquivos_xml)}] ⚠️ Pulando arquivo com nome inválido: {arquivo_xml.name}")
                    total_erros += 1
                    continue
                
                # Extrai CNPJ da chave
                cnpj = extrair_cnpj_da_chave(chave)
                if not cnpj:
                    print(f"[{idx}/{len(arquivos_xml)}] ❌ Não foi possível extrair CNPJ: {chave}")
                    total_erros += 1
                    continue
                
                # Extrai ano-mês da chave (posições 2-6: AAMM)
                try:
                    ano = '20' + chave[2:4]
                    mes = chave[4:6]
                    ano_mes = f"{ano}-{mes}"
                except:
                    print(f"[{idx}/{len(arquivos_xml)}] ❌ Erro ao extrair data da chave: {chave}")
                    total_erros += 1
                    continue
                
                # Determina pasta de destino baseada no tipo
                if tipo_pasta == 'LOCAL':
                    pasta_raiz = Path('xmls')
                else:
                    pasta_raiz = Path(pasta_storage)
                
                # Cria caminho de destino
                pasta_destino = pasta_raiz / cnpj / ano_mes / 'Eventos'
                pasta_destino.mkdir(parents=True, exist_ok=True)
                
                arquivo_destino = pasta_destino / arquivo_xml.name
                
                # Verifica se já existe
                if arquivo_destino.exists():
                    print(f"[{idx}/{len(arquivos_xml)}] ⏭️ Já existe: {cnpj}/{ano_mes}/Eventos/{arquivo_xml.name}")
                    # Remove o arquivo da pasta desconhecido (já existe no local correto)
                    arquivo_xml.unlink()
                    total_movidos += 1
                    continue
                
                # Move arquivo (copia + verifica + deleta original)
                shutil.copy2(arquivo_xml, arquivo_destino)
                
                # Verifica se foi copiado corretamente
                if arquivo_destino.exists() and arquivo_destino.stat().st_size == arquivo_xml.stat().st_size:
                    # Remove original apenas se cópia foi bem sucedida
                    arquivo_xml.unlink()
                    print(f"[{idx}/{len(arquivos_xml)}] ✅ Movido: {cnpj}/{ano_mes}/Eventos/{arquivo_xml.name}")
                    total_movidos += 1
                else:
                    print(f"[{idx}/{len(arquivos_xml)}] ❌ Erro na cópia: {arquivo_xml.name}")
                    total_erros += 1
                    
            except Exception as e:
                print(f"[{idx}/{len(arquivos_xml)}] ❌ Erro ao processar {arquivo_xml.name}: {e}")
                total_erros += 1
                continue
        
        # Remove pasta desconhecido se estiver vazia
        try:
            if pasta_desconhecido.exists():
                # Remove subpastas vazias primeiro
                for subpasta in pasta_desconhecido.rglob('*'):
                    if subpasta.is_dir() and not any(subpasta.iterdir()):
                        subpasta.rmdir()
                        print(f"🗑️ Removida pasta vazia: {subpasta}")
                
                # Remove pasta principal se estiver vazia
                if not any(pasta_desconhecido.rglob('*')):
                    pasta_desconhecido.rmdir()
                    print(f"🗑️ Removida pasta 'desconhecido' vazia: {pasta_desconhecido}")
        except Exception as e:
            print(f"⚠️ Não foi possível remover pasta desconhecido: {e}")
    
    # Resumo final
    print(f"\n{'='*60}")
    print(f"📊 RESUMO:")
    print(f"   ✅ Arquivos movidos: {total_movidos}")
    print(f"   ❌ Erros: {total_erros}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    import sys
    
    print("="*60)
    print("🔧 REORGANIZADOR DE EVENTOS 'desconhecido'")
    print("="*60)
    print()
    print("Este script move eventos da pasta 'desconhecido' para as")
    print("pastas corretas extraindo o CNPJ da chave de acesso (44 dígitos).")
    print()
    print("Exemplo de chave: 50250900924845001145550010002549351769285666")
    print("                        ^^^^^^^^^^^^^^ <- CNPJ: 00924845001145")
    print()
    
    # Verifica se foi passado caminho como argumento
    pasta_storage = None
    if len(sys.argv) > 1:
        pasta_storage = sys.argv[1]
        print(f"📂 Pasta de storage (argumento): {pasta_storage}")
        print()
        
        # Modo automático - não pede confirmação se passou argumento
        reorganizar_eventos(pasta_storage)
        print("✅ Processo concluído!")
    else:
        # Modo interativo - pergunta
        usar_storage = input("Deseja processar também a pasta de armazenamento? (s/N): ").strip().lower()
        
        if usar_storage == 's':
            pasta_storage_input = input("Digite o caminho da pasta de armazenamento: ").strip()
            if pasta_storage_input:
                pasta_storage = pasta_storage_input
                print(f"✅ Pasta de storage: {pasta_storage}")
            else:
                print("⚠️ Caminho vazio, processando apenas pasta local")
        
        print()
        confirmar = input("Confirma a reorganização? (s/N): ").strip().lower()
        
        if confirmar == 's':
            print()
            reorganizar_eventos(pasta_storage)
            print("✅ Processo concluído!")
        else:
            print("❌ Operação cancelada")
