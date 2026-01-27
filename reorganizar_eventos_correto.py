"""
Script para reorganizar eventos usando o CNPJ DO CERTIFICADO (não do emitente).

IMPORTANTE: Eventos devem ser salvos na pasta do CNPJ do certificado/destinatário,
não na pasta do emitente da nota!

Este script:
1. Busca no banco qual certificado possui cada nota (via chave)
2. Move o evento para a pasta do certificado correto
3. Remove pastas criadas incorretamente
"""

import os
import shutil
import sqlite3
from pathlib import Path

def get_certificados_cadastrados(db_path: str = "notas.db") -> dict:
    """
    Retorna dict com CNPJs dos certificados cadastrados.
    Formato: {cnpj: razao_social}
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT cnpj_cpf, razao_social FROM certificados WHERE ativo = 1")
        certificados = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return certificados
    except Exception as e:
        print(f"⚠️ Erro ao buscar certificados: {e}")
        return {}

def get_informante_por_chave(chave: str, db_path: str = "notas.db") -> str:
    """
    Busca no banco qual certificado (informante) possui a nota com essa chave.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT informante FROM notas_detalhadas WHERE chave = ? LIMIT 1",
            (chave,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row[0]
        return None
    except Exception as e:
        print(f"⚠️ Erro ao buscar informante: {e}")
        return None

def reorganizar_eventos_correto(pasta_storage: str = None):
    """
    Reorganiza eventos usando o CNPJ do certificado correto.
    """
    # 1. Busca certificados cadastrados
    certificados = get_certificados_cadastrados()
    
    if not certificados:
        print("❌ Nenhum certificado encontrado no banco!")
        return
    
    print(f"\n📋 Certificados cadastrados:")
    for cnpj, nome in certificados.items():
        print(f"   • {cnpj} - {nome}")
    print()
    
    # 2. Determina pastas para processar
    pastas_para_verificar = []
    
    # Pasta local (xmls/)
    pasta_local = Path('xmls')
    if pasta_local.exists():
        # Busca todas as subpastas que NÃO são certificados cadastrados
        for subpasta in pasta_local.iterdir():
            if subpasta.is_dir():
                nome_pasta = subpasta.name
                # Ignora certificados cadastrados
                if nome_pasta not in certificados:
                    pastas_para_verificar.append(('LOCAL', subpasta))
    
    # Pasta de storage
    if pasta_storage:
        pasta_storage_path = Path(pasta_storage)
        if pasta_storage_path.exists():
            for subpasta in pasta_storage_path.iterdir():
                if subpasta.is_dir():
                    nome_pasta = subpasta.name
                    if nome_pasta not in certificados:
                        pastas_para_verificar.append(('STORAGE', subpasta))
    
    if not pastas_para_verificar:
        print("✅ Nenhuma pasta incorreta encontrada!")
        return
    
    print(f"🔍 Encontradas {len(pastas_para_verificar)} pastas para reorganizar\n")
    
    total_movidos = 0
    total_erros = 0
    total_nao_encontrados = 0
    
    for tipo_pasta, pasta_incorreta in pastas_para_verificar:
        cnpj_incorreto = pasta_incorreta.name
        print(f"\n{'='*60}")
        print(f"📂 Processando pasta {tipo_pasta}: {cnpj_incorreto}")
        print(f"{'='*60}\n")
        
        # Busca todos os XMLs recursivamente
        arquivos_xml = list(pasta_incorreta.rglob('*.xml'))
        print(f"📄 Encontrados {len(arquivos_xml)} arquivos XML\n")
        
        for idx, arquivo_xml in enumerate(arquivos_xml, 1):
            try:
                # Extrai chave do nome do arquivo
                chave = arquivo_xml.stem
                
                # Valida chave (44 dígitos)
                if not chave.isdigit() or len(chave) != 44:
                    print(f"[{idx}/{len(arquivos_xml)}] ⚠️ Nome inválido: {arquivo_xml.name}")
                    total_erros += 1
                    continue
                
                # Busca no banco qual certificado possui essa nota
                informante = get_informante_por_chave(chave)
                
                if not informante:
                    print(f"[{idx}/{len(arquivos_xml)}] ⚠️ Nota não encontrada no banco: {chave}")
                    total_nao_encontrados += 1
                    continue
                
                # Verifica se é um certificado cadastrado
                if informante not in certificados:
                    print(f"[{idx}/{len(arquivos_xml)}] ⚠️ CNPJ {informante} não é certificado cadastrado: {chave}")
                    total_nao_encontrados += 1
                    continue
                
                # Extrai estrutura de pastas relativa (ano-mes/Eventos)
                partes_relativas = arquivo_xml.relative_to(pasta_incorreta).parts[1:]  # Remove CNPJ incorreto
                
                # Determina pasta de destino
                if tipo_pasta == 'LOCAL':
                    pasta_raiz = Path('xmls')
                else:
                    pasta_raiz = Path(pasta_storage)
                
                # Reconstrói caminho com CNPJ correto
                pasta_destino = pasta_raiz / informante
                for parte in partes_relativas[:-1]:  # Todas menos o nome do arquivo
                    pasta_destino = pasta_destino / parte
                
                pasta_destino.mkdir(parents=True, exist_ok=True)
                arquivo_destino = pasta_destino / arquivo_xml.name
                
                # Verifica se já existe
                if arquivo_destino.exists():
                    # Compara tamanhos
                    if arquivo_destino.stat().st_size == arquivo_xml.stat().st_size:
                        print(f"[{idx}/{len(arquivos_xml)}] ⏭️ Já existe: {informante}/{'/'.join(partes_relativas)}")
                        arquivo_xml.unlink()  # Remove duplicado
                        total_movidos += 1
                        continue
                
                # Move arquivo
                shutil.copy2(arquivo_xml, arquivo_destino)
                
                # Verifica se foi copiado corretamente
                if arquivo_destino.exists() and arquivo_destino.stat().st_size == arquivo_xml.stat().st_size:
                    arquivo_xml.unlink()
                    print(f"[{idx}/{len(arquivos_xml)}] ✅ Movido: {informante}/{'/'.join(partes_relativas)}")
                    total_movidos += 1
                else:
                    print(f"[{idx}/{len(arquivos_xml)}] ❌ Erro na cópia: {arquivo_xml.name}")
                    total_erros += 1
                    
            except Exception as e:
                print(f"[{idx}/{len(arquivos_xml)}] ❌ Erro: {e}")
                total_erros += 1
                continue
        
        # Remove pasta incorreta se estiver vazia
        try:
            if pasta_incorreta.exists():
                # Remove subpastas vazias
                for subpasta in list(pasta_incorreta.rglob('*'))[::-1]:
                    if subpasta.is_dir() and not any(subpasta.iterdir()):
                        subpasta.rmdir()
                        print(f"🗑️ Removida pasta vazia: {subpasta}")
                
                # Remove pasta principal se estiver vazia
                if not any(pasta_incorreta.rglob('*')):
                    pasta_incorreta.rmdir()
                    print(f"🗑️ Removida pasta incorreta: {pasta_incorreta}")
        except Exception as e:
            print(f"⚠️ Não foi possível remover pasta: {e}")
    
    # Resumo final
    print(f"\n{'='*60}")
    print(f"📊 RESUMO:")
    print(f"   ✅ Arquivos movidos: {total_movidos}")
    print(f"   ⚠️ Não encontrados no banco: {total_nao_encontrados}")
    print(f"   ❌ Erros: {total_erros}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    import sys
    
    print("="*60)
    print("🔧 REORGANIZADOR DE EVENTOS - VERSÃO CORRETA")
    print("="*60)
    print()
    print("Move eventos para a pasta do CERTIFICADO (não do emitente).")
    print("Remove pastas de CNPJs não cadastrados como certificados.")
    print()
    
    # Verifica se foi passado caminho como argumento
    pasta_storage = None
    if len(sys.argv) > 1:
        pasta_storage = sys.argv[1]
        print(f"📂 Pasta de storage: {pasta_storage}")
        print()
        
        reorganizar_eventos_correto(pasta_storage)
        print("✅ Processo concluído!")
    else:
        # Modo interativo
        usar_storage = input("Processar pasta de armazenamento? (s/N): ").strip().lower()
        
        if usar_storage == 's':
            pasta_storage = input("Caminho da pasta: ").strip()
        
        print()
        confirmar = input("Confirma a reorganização? (s/N): ").strip().lower()
        
        if confirmar == 's':
            print()
            reorganizar_eventos_correto(pasta_storage)
            print("✅ Processo concluído!")
        else:
            print("❌ Operação cancelada")
