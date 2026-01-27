"""
Script para baixar automaticamente os XSDs oficiais da NF-e/CT-e
URLs atualizadas para links diretos de download
"""
import requests
import zipfile
from pathlib import Path
import io

# URLs oficiais dos schemas (links diretos de download)
SCHEMAS_URLS = {
    'nfe_v4.00': 'http://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=hQd5culRkII=',  # PL_009i - Schemas XML v4.0
    'eventos_v1.00': 'http://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=C4gen/ckidw=',  # Eventos v1.0
    'distribuicao_v1.01': 'http://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=IZXUCNBbvYw=',  # Distribuição DFe v1.01
}

def detectar_tipo_arquivo(content):
    """Detecta se o conteúdo é ZIP ou HTML"""
    if content.startswith(b'PK'):  # ZIP magic bytes
        return 'zip'
    elif content.startswith(b'<'):  # HTML
        return 'html'
    else:
        return 'unknown'

def baixar_e_extrair_xsd(url, destino):
    """Baixa arquivo ZIP de XSD e extrai"""
    print(f"📥 Baixando: {url}")
    
    try:
        # Segue redirects automaticamente
        response = requests.get(url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        tipo = detectar_tipo_arquivo(response.content)
        print(f"✅ Download concluído: {len(response.content)} bytes (tipo: {tipo})")
        
        if tipo == 'html':
            # Salva HTML para debug
            debug_file = destino / f"debug_{hash(url)}.html"
            debug_file.write_bytes(response.content)
            print(f"⚠️ Resposta é HTML (página web). Salvo em: {debug_file.name}")
            print(f"💡 Dica: Acesse {url} no navegador para ver o link correto de download")
            return False
        
        if tipo != 'zip':
            print(f"❌ Arquivo não é ZIP (magic bytes: {response.content[:4].hex()})")
            return False
        
        # Extrai ZIP em memória
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            total_files = len(zip_ref.namelist())
            xsd_files = [f for f in zip_ref.namelist() if f.endswith('.xsd')]
            print(f"📦 ZIP contém {total_files} arquivos ({len(xsd_files)} XSD)")
            
            if not xsd_files:
                print(f"⚠️ Nenhum arquivo XSD encontrado no ZIP")
                return False
            
            print(f"📂 Extraindo para {destino}...")
            for file_info in zip_ref.filelist:
                if file_info.filename.endswith('.xsd'):
                    zip_ref.extract(file_info, destino)
                    print(f"  ✓ {file_info.filename}")
            
            print(f"✅ Extração concluída!")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro no download: {e}")
        return False
    except zipfile.BadZipFile as e:
        print(f"❌ Erro ao extrair ZIP: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # Define diretório de destino
    base_dir = Path(__file__).parent
    xsd_dir = base_dir / "Arquivo_xsd"
    
    print("=" * 80)
    print("DOWNLOAD AUTOMÁTICO DE SCHEMAS XSD (NF-e/CT-e/Distribuição)")
    print("=" * 80)
    print(f"\n📁 Destino: {xsd_dir}")
    
    # Verifica se já existem XSDs
    if xsd_dir.exists():
        xsd_existentes = list(xsd_dir.glob('*.xsd'))
        if xsd_existentes:
            print(f"✅ Pasta já contém {len(xsd_existentes)} arquivos XSD")
            print(f"\nExemplos:")
            for xsd in sorted(xsd_existentes)[:5]:
                print(f"  • {xsd.name}")
            if len(xsd_existentes) > 5:
                print(f"  ... e mais {len(xsd_existentes) - 5} arquivos")
            
            print(f"\n💡 Os XSD já estão disponíveis e prontos para uso!")
            print(f"   Para validação de eventos NF-e, use: leiauteEvento_v1.00.xsd")
            return
    
    print("\n")
    
    # Cria diretório se não existir
    xsd_dir.mkdir(exist_ok=True)
    
    # Baixa cada pacote
    sucesso = 0
    total = len(SCHEMAS_URLS)
    
    for nome, url in SCHEMAS_URLS.items():
        print(f"\n{'='*80}")
        print(f"Pacote: {nome}")
        print(f"{'='*80}")
        
        if baixar_e_extrair_xsd(url, xsd_dir):
            sucesso += 1
        else:
            print(f"⚠️ Falha ao processar {nome}")
    
    print(f"\n{'='*80}")
    print(f"RESUMO: {sucesso}/{total} pacotes baixados com sucesso")
    print(f"{'='*80}\n")
    
    if sucesso == total:
        print("✅ Todos os schemas foram atualizados!")
    elif sucesso > 0:
        print(f"⚠️ Apenas {sucesso} de {total} pacotes foram baixados.")
        print("💡 Os XSD existentes na pasta já podem ser suficientes.")
    else:
        print("❌ Nenhum schema foi baixado.")
        print("💡 ALTERNATIVA: Baixe manualmente de:")
        print("   https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=Iy/5Qol1YbE=")
        print("   Procure por 'Pacote de Liberação' e extraia na pasta Arquivo_xsd/")

if __name__ == "__main__":
    main()
