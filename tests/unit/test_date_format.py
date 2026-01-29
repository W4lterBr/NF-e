#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Simula a função _format_date_br
def _format_date_br(date_str: str) -> str:
    """Converte data de AAAA-MM-DD para DD/MM/AAAA."""
    if not date_str:
        return ""
    try:
        # Se já está no formato DD/MM/AAAA, retorna como está
        if "/" in date_str:
            return date_str
        # Converte de AAAA-MM-DD para DD/MM/AAAA
        date_part = date_str[:10]  # Pega apenas a parte da data
        if len(date_part) == 10 and date_part[4] == '-' and date_part[7] == '-':
            ano, mes, dia = date_part.split('-')
            return f"{dia}/{mes}/{ano}"
        return date_str
    except Exception as e:
        return f"ERRO: {e}"

# Testa com a data correta do banco
data_banco = "2025-11-07"
print(f"Data no banco: {data_banco}")
print(f"Data formatada: {_format_date_br(data_banco)}")
print(f"Esperado: 07/11/2025")

# Testa com chave (se estiver pegando da chave por engano)
chave = "52251122103593000154550010000006731368411170"
print(f"\nChave: {chave}")
print(f"Posições 2-4 (AA): {chave[2:4]}")
print(f"Posições 4-6 (MM): {chave[4:6]}")
print(f"Posições 6-8 (DD): {chave[6:8]}")
print(f"Data extraída da chave: 20{chave[2:4]}-{chave[4:6]}-{chave[6:8]}")
print(f"Formatada: {_format_date_br(f'20{chave[2:4]}-{chave[4:6]}-{chave[6:8]}')}")
