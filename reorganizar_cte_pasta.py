"""
Script para reorganizar CTes que foram salvos em pasta CTe fora da estrutura de data.
Move arquivos de: 99-JL COMERCIO/CTe/
Para: 99-JL COMERCIO/YYYY-MM/CTe/
"""

import os
import sys
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime

# Adiciona o diretório do projeto ao path para importar módulos
sys.path.insert(0, str(Path(__file__).parent))

def extract_date_from_cte(xml_path):
    """Extrai a data de emissão de um CT-e"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Namespace do CT-e
        ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
        
        # Tenta extrair data
        ide = root.find('.//cte:ide', ns)
        if ide is not None:
            # dhEmi é preferido (data e hora)
            dhEmi = ide.findtext('cte:dhEmi', None, ns)
            if dhEmi:
                # dhEmi formato: 2025-01-09T15:30:00-03:00
                data_str = dhEmi.split('T')[0]
                return data_str[:7]  # Retorna YYYY-MM
            
            # Fallback: dEmi (apenas data)
            dEmi = ide.findtext('cte:dEmi', None, ns)
            if dEmi:
                return dEmi[:7]
        
        return None
    except Exception as e:
        print(f"  ❌ Erro ao ler XML {xml_path.name}: {e}")
        return None

def main():
    print("=" * 70)
    print("REORGANIZAÇÃO DE CTE - Corrigir estrutura de pastas")
    print("=" * 70)
    
    # Verifica se a pasta de storage existe
    storage_path = Path("c:/Arquivo Walter - Empresas/Notas/NFs")
    if not storage_path.exists():
        print(f"❌ Pasta de storage não encontrada: {storage_path}")
        return
    
    print(f"\n📂 Buscando pastas 'CTe' fora da estrutura de data em: {storage_path}\n")
    
    movidos = 0
    erros = 0
    
    # Procura todas as pastas CTe que estão diretamente sob certificado (sem ano-mes)
    for cert_folder in storage_path.iterdir():
        if not cert_folder.is_dir():
            continue
        
        # Verifica se há pasta CTe diretamente sob o certificado
        cte_folder = cert_folder / "CTe"
        if not cte_folder.exists():
            continue
        
        print(f"✅ Encontrada pasta incorreta: {cte_folder.relative_to(storage_path)}")
        
        # Lista todos os XMLs nessa pasta
        xml_files = list(cte_folder.glob("*.xml"))
        if not xml_files:
            print(f"  ⚠️ Pasta vazia - removendo...")
            try:
                cte_folder.rmdir()
            except:
                pass
            continue
        
        print(f"  📄 {len(xml_files)} arquivo(s) encontrado(s)")
        
        # Processa cada XML
        for xml_file in xml_files:
            try:
                # Extrai data do XML
                ano_mes = extract_date_from_cte(xml_file)
                
                if not ano_mes:
                    print(f"  ⚠️ Não foi possível extrair data de {xml_file.name} - pulando")
                    erros += 1
                    continue
                
                # Define pasta destino correta: CERT/YYYY-MM/CTe/
                pasta_destino = cert_folder / ano_mes / "CTe"
                pasta_destino.mkdir(parents=True, exist_ok=True)
                
                # Move o arquivo
                destino = pasta_destino / xml_file.name
                
                if destino.exists():
                    print(f"  ⚠️ Arquivo já existe no destino: {destino.relative_to(storage_path)}")
                    # Compara tamanhos
                    if xml_file.stat().st_size == destino.stat().st_size:
                        print(f"    ℹ️ Tamanhos idênticos - removendo duplicado")
                        xml_file.unlink()
                    else:
                        print(f"    ⚠️ Tamanhos diferentes - mantendo ambos com sufixo")
                        destino = pasta_destino / f"{xml_file.stem}_dup{xml_file.suffix}"
                        shutil.move(str(xml_file), str(destino))
                else:
                    shutil.move(str(xml_file), str(destino))
                    print(f"  ✅ Movido: {xml_file.name} → {destino.relative_to(storage_path)}")
                
                # Verifica se há PDF correspondente
                pdf_file = xml_file.with_suffix('.pdf')
                if pdf_file.exists():
                    pdf_destino = destino.with_suffix('.pdf')
                    if not pdf_destino.exists():
                        shutil.move(str(pdf_file), str(pdf_destino))
                        print(f"  ✅ PDF movido também")
                
                movidos += 1
                
            except Exception as e:
                print(f"  ❌ Erro ao processar {xml_file.name}: {e}")
                erros += 1
        
        # Remove pasta CTe se estiver vazia
        try:
            if not any(cte_folder.iterdir()):
                cte_folder.rmdir()
                print(f"  🗑️ Pasta CTe removida (vazia)")
        except:
            pass
    
    print("\n" + "=" * 70)
    print(f"✅ Reorganização concluída!")
    print(f"   📦 {movidos} arquivo(s) movido(s)")
    if erros > 0:
        print(f"   ⚠️ {erros} erro(s)")
    print("=" * 70)

if __name__ == "__main__":
    main()
