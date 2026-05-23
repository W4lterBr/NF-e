# -*- coding: utf-8 -*-
"""
ROTINA DE MONITORAMENTO - NFS-e ADN Nacional
Executa busca incremental para todos os certificados cadastrados
Recomendado: Executar diariamente ou semanalmente
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from nfe_search import DatabaseManager, logger
from modules.nfse_service import NFSeService

print("="*80)
print("🔄 ROTINA DE MONITORAMENTO - NFS-e")
print("="*80)
print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print("="*80)
print()

# Conecta ao banco
db_path = os.path.join(os.path.dirname(__file__), 'notas.db')
db = DatabaseManager(db_path)

# Busca todos os certificados cadastrados
certificados = db.get_certificados()

if not certificados:
    print("❌ Nenhum certificado cadastrado")
    sys.exit(1)

print(f"📜 {len(certificados)} certificado(s) cadastrado(s)")
print()

total_novos = 0
erros = []

for idx, (cnpj, caminho, senha, informante, cuf) in enumerate(certificados, 1):
    print("="*80)
    print(f"🔍 CERTIFICADO {idx}/{len(certificados)}")
    print("="*80)
    print(f"   CNPJ: {cnpj}")
    print(f"   Informante: {informante}")
    print()
    
    try:
        # Verifica último NSU
        last_nsu = db.get_last_nsu_nfse(informante)
        print(f"   📊 Último NSU processado: {last_nsu}")
        
        # Inicializa serviço
        nfse_svc = NFSeService(caminho, senha, cnpj, cuf, ambiente='producao')
        print(f"   ✅ Serviço ADN inicializado")
        print()
        print(f"   🔄 Consultando novos documentos...")
        print()
        
        # Consulta próximos NSUs (em lotes de 50)
        nsu_atual = int(last_nsu) + 1
        max_tentativas = 5  # Tenta 5 lotes vazios antes de parar
        tentativas_vazias = 0
        novos_docs = 0
        
        while tentativas_vazias < max_tentativas:
            try:
                resp = nfse_svc.consultar_nsu(f"{nsu_atual:015d}")
                
                if not resp:
                    print(f"      NSU {nsu_atual:015d}: Vazio")
                    tentativas_vazias += 1
                    nsu_atual += 1
                    continue
                
                if isinstance(resp, dict):
                    lote_dfe = resp.get('LoteDFe', [])
                    status = resp.get('StatusProcessamento', '')
                    
                    if status == 'NENHUM_DOCUMENTO_LOCALIZADO':
                        print(f"      NSU {nsu_atual:015d}: Sem documentos")
                        tentativas_vazias += 1
                    elif status == 'DOCUMENTOS_LOCALIZADOS' and lote_dfe:
                        doc_count = len(lote_dfe)
                        print(f"      NSU {nsu_atual:015d}: ✅ {doc_count} documento(s)")
                        novos_docs += doc_count
                        tentativas_vazias = 0  # Reset contador
                        
                        # Processa e salva documentos
                        from nfe_search import salvar_nfse_detalhada
                        import base64
                        import gzip
                        
                        for doc_info in lote_dfe:
                            try:
                                doc_nsu = doc_info.get('NSU')
                                doc_tipo = doc_info.get('TipoDocumento', '')
                                doc_chave = doc_info.get('ChaveAcesso', '')
                                doc_xml_b64 = doc_info.get('ArquivoXml', '')
                                
                                if doc_xml_b64:
                                    # Decodifica e descomprime
                                    xml_comprimido = base64.b64decode(doc_xml_b64)
                                    xml = gzip.decompress(xml_comprimido).decode('utf-8')
                                    
                                    # Salva
                                    if salvar_nfse_detalhada(xml, str(doc_nsu), informante):
                                        print(f"         ✅ {doc_tipo} - Chave: {doc_chave[:30]}...")
                                    
                            except Exception as e:
                                print(f"         ❌ Erro ao processar documento: {e}")
                        
                        # Atualiza último NSU
                        db.set_last_nsu_nfse(informante, f"{nsu_atual:015d}")
                    else:
                        print(f"      NSU {nsu_atual:015d}: {status}")
                        tentativas_vazias += 1
                
                nsu_atual += 1
                
            except Exception as e:
                print(f"      ❌ Erro no NSU {nsu_atual:015d}: {e}")
                tentativas_vazias += 1
                nsu_atual += 1
        
        print()
        if novos_docs > 0:
            print(f"   ✅ {novos_docs} novos documentos baixados")
            total_novos += novos_docs
        else:
            print(f"   ℹ️  Nenhum documento novo encontrado")
        
    except Exception as e:
        erro_msg = f"❌ Erro ao processar certificado {cnpj}: {e}"
        print(f"   {erro_msg}")
        erros.append(erro_msg)
    
    print()

# Resumo final
print("="*80)
print("📊 RESUMO DA EXECUÇÃO")
print("="*80)
print(f"   Certificados processados: {len(certificados)}")
print(f"   Novos documentos: {total_novos}")
print(f"   Erros: {len(erros)}")
print()

if erros:
    print("⚠️  ERROS ENCONTRADOS:")
    for erro in erros:
        print(f"   • {erro}")
    print()

if total_novos > 0:
    print("✅ Novos documentos foram baixados e salvos!")
    print("   Verifique:")
    print(f"   • Banco de dados: {db_path}")
    print(f"   • XMLs exportados: xmls/")
else:
    print("ℹ️  Nenhum documento novo no momento")
    print()
    print("💡 LEMBRE-SE:")
    print("   • A API só retorna notas distribuídas oficialmente")
    print("   • Notas no portal web podem não estar na API ainda")
    print("   • Execute esta rotina regularmente para manter atualizado")

print("="*80)
print(f"🕐 Finalizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print("="*80)
