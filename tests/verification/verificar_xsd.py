"""Verifica versões dos XSD existentes"""
from pathlib import Path
import os
from datetime import datetime

xsd_dir = Path(__file__).parent / "Arquivo_xsd"

# XSD principais e suas versões esperadas
xsd_principais = {
    'leiauteEvento_v1.00.xsd': 'Eventos NF-e v1.00',
    'leiauteNFe_v4.00.xsd': 'Layout NF-e v4.00',
    'nfe_v4.00.xsd': 'NF-e v4.00',
    'cte_v4.00.xsd': 'CT-e v4.00',
    'distDFeInt_v1.01.xsd': 'Distribuição DFe v1.01',
    'retEnvEvento_v1.00.xsd': 'Retorno Evento v1.00 (se existir)',
    'tiposBasico_v1.03.xsd': 'Tipos Básicos v1.03',
    'xmldsig-core-schema_v1.01.xsd': 'XML Signature v1.01',
}

print("=" * 80)
print("VERIFICAÇÃO DE XSD - Versões e Datas")
print("=" * 80)
print(f"\n📁 Pasta: {xsd_dir}\n")

if not xsd_dir.exists():
    print("❌ Pasta Arquivo_xsd não encontrada!")
    exit(1)

total_xsd = len(list(xsd_dir.glob('*.xsd')))
print(f"Total de arquivos XSD: {total_xsd}\n")

print("📋 XSD Principais:\n")
encontrados = 0
for xsd_file, descricao in xsd_principais.items():
    path = xsd_dir / xsd_file
    if path.exists():
        stat = os.stat(path)
        tamanho = stat.st_size
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        print(f"✅ {xsd_file}")
        print(f"   {descricao}")
        print(f"   Tamanho: {tamanho:,} bytes | Modificado: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        encontrados += 1
    else:
        print(f"❌ {xsd_file} - NÃO ENCONTRADO")
        print(f"   {descricao}\n")

print("=" * 80)
print(f"Resultado: {encontrados}/{len(xsd_principais)} XSD principais encontrados")
print("=" * 80)

if encontrados == len(xsd_principais) or encontrados >= len(xsd_principais) - 1:
    print("\n✅ XSD estão completos e prontos para uso!")
else:
    print(f"\n⚠️ Faltam {len(xsd_principais) - encontrados} XSD principais")
    print("💡 Baixe o Pacote de Liberação mais recente do Portal da NF-e")
