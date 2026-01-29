#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de manifestacao usando API BrasilNFe
https://brasilnfe.com.br/api/eventos
"""
import requests
import json

# Dados da chave do usuario
chave = "53251257650492000188550010000334281113441317"

# Configuracao da API
API_URL = "https://api.brasilnfe.com.br/services/fiscal/ManifestarNotaFiscal"
API_TOKEN = "SEU_TOKEN_AQUI"  # Precisa obter no site BrasilNFe

# Payload conforme documentacao
payload = {
    "TipoAmbiente": 1,  # 1=Producao, 2=Homologacao
    "TipoManifestacao": 2,  # 1=Confirmacao, 2=Ciencia, 3=Desconhecimento, 4=Nao Realizada
    "Chave": chave,
    "NumeroSequencial": 1
}

print("=" * 80)
print("TESTE DE MANIFESTACAO - API BRASILNFE")
print("=" * 80)
print(f"\nChave: {chave}")
print(f"Tipo: Ciencia da Operacao (2)")
print(f"Ambiente: Producao (1)")
print(f"\nPayload:")
print(json.dumps(payload, indent=2))

# Verificar se tem token
if API_TOKEN == "SEU_TOKEN_AQUI":
    print("\n" + "=" * 80)
    print("ATENCAO: Necessario configurar API_TOKEN")
    print("=" * 80)
    print("\nPara usar a API BrasilNFe:")
    print("1. Criar conta em https://brasilnfe.com.br/")
    print("2. Obter token de API")
    print("3. Configurar certificado digital na plataforma")
    print("4. Atualizar API_TOKEN neste script")
    print("\nVANTAGENS:")
    print("- Nao precisa lidar com xmlsec localmente")
    print("- Assinatura feita nos servidores deles")
    print("- Suporte tecnico disponivel")
    print("- Já testado e funcional com SEFAZ")
    print("\nOBS: Servico pago (verificar planos no site)")
    exit(0)

# Headers
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_TOKEN}"
}

print(f"\n{'=' * 80}")
print("Enviando para API BrasilNFe...")
print(f"{'=' * 80}\n")

try:
    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=30
    )
    
    print(f"Status HTTP: {response.status_code}")
    print(f"\nResposta:")
    print(json.dumps(response.json(), indent=2))
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\n{'=' * 80}")
        print("RESULTADO:")
        print(f"{'=' * 80}")
        print(f"Status: {data.get('Status')}")
        print(f"Evento: {data.get('DsEvento')}")
        print(f"Motivo: {data.get('DsMotivo')}")
        print(f"Protocolo: {data.get('NuProtocolo')}")
        print(f"Codigo SEFAZ: {data.get('CodStatusRespostaSefaz')}")
        
        if data.get('Status') == 1:
            print("\nSUCESSO! Evento processado pela SEFAZ")
        elif data.get('Status') == 2:
            print("\nAguardando processamento...")
        elif data.get('Status') == 3:
            print(f"\nERRO: {data.get('Error')}")
    else:
        print(f"\nERRO HTTP {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"\nERRO ao chamar API: {e}")
    import traceback
    traceback.print_exc()
