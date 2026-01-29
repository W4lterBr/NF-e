#!/usr/bin/env python3
"""
Script de teste para diagnosticar erro 297 na manifestação
"""
import sys
import os
from pathlib import Path

# Adicionar diretório ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from modules.manifestacao_service import ManifestacaoService
from modules.database import DatabaseManager
import logging

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler()]
)

def main():
    print("=" * 80)
    print("TESTE DE MANIFESTAÇÃO - DIAGNÓSTICO ERRO 297")
    print("=" * 80)
    
    # Dados de teste
    cnpj = "33251845000109"
    chave = "50251042263870000101550010009997851162320151"  # ✅ NF-e modelo 55 (44 dígitos)
    tipo_evento = "210210"  # Ciência da Operação
    
    # Carregar certificado do banco usando a classe DatabaseManager
    print("\nBuscando certificado no banco de dados...")
    db_path = BASE_DIR / "notas.db"  # 🔧 MUDANÇA: Usar banco real
    db = DatabaseManager(db_path)
    certs = db.load_certificates()
    
    cert_info = None
    for cert in certs:
        if cert.get('informante') == cnpj:
            cert_info = cert
            break
    
    if not cert_info:
        print(f"ERRO: Certificado nao encontrado para CNPJ {cnpj}")
        print(f"   Certificados disponiveis:")
        for cert in certs:
            print(f"      - {cert.get('informante')}: {cert.get('razao_social')}")
        return
    
    cert_path = cert_info['caminho']
    cert_senha = cert_info['senha']  # Já descriptografada pelo load_certificates()
    cert_cnpj = cert_info['cnpj_cpf']
    
    print(f"OK Certificado encontrado:")
    print(f"   Razao Social: {cert_info.get('razao_social', 'N/A')}")
    print(f"   CNPJ: {cert_cnpj}")
    print(f"   Caminho: {cert_path}")
    print(f"   Senha: {'*' * len(cert_senha) if cert_senha else '(vazia)'}")
    
    if not Path(cert_path).exists():
        print(f"\nERRO: Arquivo do certificado nao encontrado: {cert_path}")
        return
    
    print(f"\nTestando manifestacao:")
    print(f"   Chave NF-e: {chave}")
    print(f"   Tipo evento: {tipo_evento} (Ciencia da Operacao)")
    print(f"   CNPJ destinatario: {cnpj}")
    print(f"\n{'=' * 80}\n")
    
    try:
        # Criar serviço
        service = ManifestacaoService(cert_path, cert_senha)
        
        # Enviar manifestação
        sucesso, protocolo, mensagem, xml_resposta = service.enviar_manifestacao(
            chave=chave,
            tipo_evento=tipo_evento,
            cnpj_destinatario=cert_cnpj,
            justificativa=None  # Ciência não precisa de justificativa
        )
        
        print(f"\n{'=' * 80}")
        print("RESULTADO:")
        print(f"{'=' * 80}")
        print(f"Sucesso: {sucesso}")
        print(f"Protocolo: {protocolo}")
        print(f"Mensagem: {mensagem}")
        
        if xml_resposta:
            # Extrair cStat da resposta
            import re
            match = re.search(r'<cStat>(\d+)</cStat>', xml_resposta)
            if match:
                cstat = match.group(1)
                print(f"cStat: {cstat}")
                
                if cstat == "135":
                    print("\n=== SUCESSO! Evento registrado e vinculado a NF-e! ===")
                elif cstat == "297":
                    print("\nERRO 297: Assinatura difere do calculado")
                    print("   O problema PERSISTE - precisa ajustar a assinatura")
                elif cstat == "215":
                    print("\nERRO 215: Falha no esquema XML")
                    print("   Problema de namespace")
                elif cstat == "588":
                    print("\nERRO 588: Caracteres de edicao na mensagem")
                    print("   Problema de formatacao")
                else:
                    print(f"\nCodigo de status: {cstat}")
        
        print(f"{'=' * 80}\n")
        
    except Exception as e:
        print(f"\n{'=' * 80}")
        print(f"ERRO DURANTE TESTE:")
        print(f"{'=' * 80}")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'=' * 80}\n")

if __name__ == "__main__":
    main()
