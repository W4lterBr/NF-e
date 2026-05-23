"""
Script para importar NFS-e existentes em xmls/ para o banco notas_detalhadas
"""
import sqlite3
from pathlib import Path
from lxml import etree
from datetime import datetime

DB_PATH = Path("notas_test.db")

def extrair_dados_nfse(xml_path):
    """Extrai dados de uma NFS-e para salvar no banco"""
    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        tree = etree.fromstring(xml_content.encode('utf-8'))
        ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}
        
        # Extrai chave de acesso
        inf_nfse = tree.find('.//nfse:infNFSe', namespaces=ns)
        if inf_nfse is None:
            print(f"   ⚠️  infNFSe não encontrado em {xml_path.name}")
            return None
        
        chave_id = inf_nfse.get('Id', '')
        if not chave_id:
            print(f"   ⚠️  Atributo Id não encontrado em {xml_path.name}")
            return None
        
        # Remove prefixo "NFS" da chave
        chave = chave_id[3:] if chave_id.startswith('NFS') else chave_id
        
        # Extrai dados básicos
        # Número da NFS-e (pode estar em nNFSe ou nDFSe)
        numero = tree.findtext('.//nfse:nNFSe', namespaces=ns) or tree.findtext('.//nfse:nDFSe', namespaces=ns) or ''
        
        # Data de emissão (pode estar em dhEmi ou dhProc)
        data_emissao = tree.findtext('.//nfse:dhEmi', namespaces=ns) or tree.findtext('.//nfse:dhProc', namespaces=ns) or ''
        
        # Prestador (emissor) - estrutura: emit > CNPJ
        cnpj_prestador = tree.findtext('.//nfse:emit/nfse:CNPJ', namespaces=ns) or ''
        nome_prestador = tree.findtext('.//nfse:emit/nfse:xNome', namespaces=ns) or ''
        
        # Tomador (destinatário) - estrutura: toma > CNPJ
        cnpj_tomador = tree.findtext('.//nfse:toma/nfse:CNPJ', namespaces=ns) or ''
        ie_tomador = ''  # NFSe nacional não tem IE do tomador
        
        # Valores - estrutura: valores > vServPrest > vServ ou valores > vLiq
        valor_servicos = tree.findtext('.//nfse:vServ', namespaces=ns) or tree.findtext('.//nfse:vLiq', namespaces=ns) or '0'
        valor_iss = tree.findtext('.//nfse:vISSQN', namespaces=ns) or '0'
        base_iss = tree.findtext('.//nfse:vBC', namespaces=ns) or '0'
        
        # UF do prestador - estrutura: emit > enderNac > UF
        uf = tree.findtext('.//nfse:emit/nfse:enderNac/nfse:UF', namespaces=ns) or ''
        
        # Natureza (descrição do serviço) - estrutura: serv > cServ > xDescServ
        discriminacao = tree.findtext('.//nfse:xDescServ', namespaces=ns) or ''
        natureza = discriminacao[:100] if discriminacao else ''  # Limita a 100 caracteres
        
        # Extrai informante do caminho (estrutura: xmls/{CNPJ}/{ANO-MES}/NFSe/)
        try:
            partes = xml_path.parts
            if 'xmls' in partes:
                idx_xmls = partes.index('xmls')
                informante = partes[idx_xmls + 1]  # CNPJ logo após 'xmls'
            else:
                informante = cnpj_prestador  # Fallback
        except:
            informante = cnpj_prestador
        
        # Formata data para ISO (YYYY-MM-DD)
        if data_emissao:
            try:
                # Assume formato YYYY-MM-DDTHH:MM:SS
                data_iso = data_emissao.split('T')[0]
            except:
                data_iso = data_emissao[:10]
        else:
            data_iso = ''
        
        return {
            'chave': chave,
            'numero': numero,
            'data_emissao': data_iso,
            'tipo': 'NFS-e',
            'valor': valor_servicos,
            'cnpj_emitente': cnpj_prestador,
            'nome_emitente': nome_prestador,
            'cnpj_destinatario': cnpj_tomador,
            'ie_tomador': ie_tomador,
            'uf': uf,
            'natureza': natureza,
            'base_icms': base_iss,  # Para NFSe, usamos base ISS
            'valor_icms': valor_iss,  # Para NFSe, usamos valor ISS
            'status': 'Autorizado',
            'xml_status': 'COMPLETO',
            'informante': informante,
            'atualizado_em': datetime.now().isoformat(),
            'cfop': '',
            'ncm': '',
            'vencimento': ''
        }
    
    except Exception as e:
        print(f"   ❌ Erro ao processar {xml_path.name}: {e}")
        return None

def importar_nfse():
    """Importa todas as NFS-e existentes em xmls/"""
    print("\n" + "="*80)
    print("IMPORTANDO NFS-e EXISTENTES PARA O BANCO")
    print("="*80 + "\n")
    
    # Busca todos os XMLs de NFS-e
    base_dir = Path("xmls")
    if not base_dir.exists():
        print("❌ Pasta xmls/ não encontrada!")
        return
    
    xmls_nfse = list(base_dir.rglob("NFSe/*.xml"))
    total = len(xmls_nfse)
    
    if total == 0:
        print("Nenhum XML de NFS-e encontrado em xmls/")
        return
    
    print(f"Encontrados {total} XMLs de NFS-e\n")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    importados = 0
    erros = 0
    duplicados = 0
    
    for idx, xml_path in enumerate(xmls_nfse, 1):
        print(f"[{idx}/{total}] Processando {xml_path.name}...", end=" ")
        
        # Extrai dados
        dados = extrair_dados_nfse(xml_path)
        if not dados:
            erros += 1
            continue
        
        # Verifica se já existe
        cursor.execute("SELECT chave FROM notas_detalhadas WHERE chave = ?", (dados['chave'],))
        if cursor.fetchone():
            print(f"⏭️  Já existe (chave: {dados['chave'][:20]}...)")
            duplicados += 1
            continue
        
        # Registra XML baixado
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO xmls_baixados
                (chave, cnpj_cpf, caminho_arquivo, baixado_em)
                VALUES (?, ?, ?, ?)
            ''', (dados['chave'], dados['informante'], str(xml_path), datetime.now().isoformat()))
        except Exception as e:
            print(f"⚠️  Erro ao registrar XML: {e}")
        
        # Salva nota detalhada
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO notas_detalhadas (
                    chave, numero, data_emissao, tipo, valor, cnpj_emitente, nome_emitente,
                    cnpj_destinatario, ie_tomador, uf, natureza, base_icms, valor_icms,
                    status, xml_status, informante, atualizado_em, cfop, ncm, vencimento
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dados['chave'], dados['numero'], dados['data_emissao'], dados['tipo'],
                dados['valor'], dados['cnpj_emitente'], dados['nome_emitente'],
                dados['cnpj_destinatario'], dados['ie_tomador'], dados['uf'],
                dados['natureza'], dados['base_icms'], dados['valor_icms'],
                dados['status'], dados['xml_status'], dados['informante'],
                dados['atualizado_em'], dados['cfop'], dados['ncm'], dados['vencimento']
            ))
            
            print(f"✅ Importado (Nº {dados['numero']}, R$ {float(dados['valor']):,.2f})")
            importados += 1
            
        except Exception as e:
            print(f"❌ Erro ao salvar no banco: {e}")
            erros += 1
    
    # Commit final
    conn.commit()
    conn.close()
    
    # Resumo
    print("\n" + "="*80)
    print("📊 RESUMO DA IMPORTAÇÃO")
    print("="*80)
    print(f"✅ Importados com sucesso: {importados}")
    print(f"⏭️  Já existiam no banco: {duplicados}")
    print(f"❌ Erros: {erros}")
    print(f"📁 Total processado: {total}")
    print("="*80 + "\n")

if __name__ == "__main__":
    importar_nfse()
