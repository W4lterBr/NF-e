#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste SIMPLIFICADO para diagnosticar erro 297 na manifestacao
Usa a mesma estrutura do codigo principal que funciona
"""
import sys
import os
from pathlib import Path

# Adicionar diretorio ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from modules.manifestacao_service import ManifestacaoService
from modules.database import DatabaseManager
import logging

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

def main():
    print("=" * 80)
    print("TESTE DE ASSINATURA - DIAGNOSTICO COMPLETO")
    print("=" * 80)
    
    # Dados de teste com a chave do usuario
    cnpj = "49068153000160"
    chave = "53251257650492000188550010000334281113441317"
    tipo_evento = "210200"  # Ciencia da Operacao
    
    # Carregar certificado do banco (tenta notas.db local)
    print("\nBuscando certificado no banco de dados...")
    db_path = BASE_DIR / "notas.db"
    
    if not db_path.exists():
        print(f"ERRO: notas.db nao encontrado em {db_path}")
        return
    
    db = DatabaseManager(db_path)
    certs = db.load_certificates()
    
    cert_info = None
    for cert in certs:
        if cert.get('cnpj_cpf') == cnpj:
            cert_info = cert
            break
    
    if not cert_info:
        print(f"ERRO: Certificado nao encontrado para CNPJ {cnpj}")
        print(f"   Certificados disponiveis:")
        for cert in certs:
            print(f"      - {cert.get('cnpj_cpf')}: {cert.get('razao_social')}")
        return
    
    cert_path = cert_info['caminho']
    cert_senha = cert_info['senha']  # Ja descriptografada pelo load_certificates()
    cert_cnpj = cert_info['cnpj_cpf']
    
    print(f"OK - Certificado encontrado:")
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
        # Criar servico (aqui que carrega o PFX e assina)
        print("Carregando certificado...")
        service = ManifestacaoService(cert_path, cert_senha)
        print("OK - Certificado carregado\n")
        
        # Enviar manifestacao (aqui que assina e envia)
        print("Enviando manifestacao para SEFAZ...")
        sucesso, protocolo, mensagem, xml_resposta = service.enviar_manifestacao(
            chave=chave,
            tipo_evento=tipo_evento,
            cnpj_destinatario=cert_cnpj,
            justificativa=None  # Ciencia nao precisa de justificativa
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
                    print("\nSUCESSO! Evento registrado.")
                elif cstat == "573":
                    print("\nAVISO: Duplicidade de Evento (ja foi registrado antes)")
                elif cstat == "297":
                    print("\nERRO 297: Assinatura difere do calculado")
                    print("   - DigestValue esta correto?")
                    print("   - SignatureValue esta correto?")
                    print("   - Transforms estao corretos?")
                elif cstat == "588":
                    print("\nERRO 588: Caracteres de edicao nao permitidos")
                    print("   - Verificar espacos em branco no XML")
                else:
                    print(f"\nERRO {cstat}: {mensagem}")
        
    except Exception as e:
        print(f"\nERRO ao executar teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
