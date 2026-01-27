import re

nome_cert = "79-ALFA COMPUTADORES"
print(f"Original: {nome_cert}")

# Regex atual (problemático)
nome_limpo = re.sub(r'[\\/*?:"<>|]', "_", nome_cert).strip()
print(f"Com regex atual: '{nome_limpo}'")

# O problema: hífen não está na lista, mas alguma coisa está removendo ele
# Vamos testar o que está acontecendo
print(f"Apenas strip(): '{nome_cert.strip()}'")
