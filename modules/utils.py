# modules/utils.py
"""
Utilitários gerais para o sistema BOT NFe
"""

import re
import logging
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

def only_digits(text: Optional[str]) -> str:
    """
    Extrai apenas dígitos de uma string
    
    Args:
        text: String de entrada
        
    Returns:
        String contendo apenas dígitos
    """
    if not text:
        return ""
    return "".join(filter(str.isdigit, text))

def format_currency(value: Any) -> str:
    """
    Formata valor para moeda brasileira (R$)
    
    Args:
        value: Valor a ser formatado (float, str, int)
        
    Returns:
        String formatada como moeda brasileira
    """
    try:
        if isinstance(value, str):
            if "R$" in value:
                return value
            # Remove formatação existente e converte
            clean_value = value.replace(".", "").replace(",", ".")
            value = float(clean_value)
        
        if isinstance(value, (int, float)):
            # Formata como moeda brasileira
            formatted = f"R$ {float(value):,.2f}"
            # Ajusta separadores para padrão brasileiro
            return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        
        return str(value or "R$ 0,00")
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Erro ao formatar valor {value}: {e}")
        return str(value or "R$ 0,00")

def format_date(date_str: Optional[str], input_format: str = "auto", output_format: str = "%d/%m/%Y") -> str:
    """
    Formata string de data para exibição
    
    Args:
        date_str: String da data
        input_format: Formato de entrada ('auto' para detecção automática)
        output_format: Formato de saída
        
    Returns:
        Data formatada ou string original se erro
    """
    if not date_str:
        return ""
    
    try:
        # Remove parte de tempo se presente
        if "T" in date_str:
            date_str = date_str.split("T")[0]
        
        # Se já está no formato desejado, retorna
        if "/" in date_str and date_str.count("/") == 2:
            return date_str
        
        # Tenta fazer parse automático
        if input_format == "auto":
            dt = datetime.fromisoformat(date_str)
        else:
            dt = datetime.strptime(date_str, input_format)
        
        return dt.strftime(output_format)
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Erro ao formatar data {date_str}: {e}")
        return date_str

def format_cnpj_cpf(document: str) -> str:
    """
    Formata CNPJ ou CPF com máscaras
    
    Args:
        document: String com apenas dígitos ou já formatada
        
    Returns:
        Documento formatado com máscara
    """
    digits = only_digits(document)
    
    if len(digits) == 14:  # CNPJ
        return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
    elif len(digits) == 11:  # CPF
        return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
    else:
        return document  # Retorna original se não for CNPJ nem CPF

def validate_cnpj(cnpj: str) -> bool:
    """
    Valida CNPJ usando algoritmo oficial
    
    Args:
        cnpj: String do CNPJ
        
    Returns:
        True se válido, False caso contrário
    """
    cnpj = only_digits(cnpj)
    
    if len(cnpj) != 14:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cnpj == cnpj[0] * 14:
        return False
    
    # Calcula primeiro dígito verificador
    weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_result = sum(int(cnpj[i]) * weights[i] for i in range(12))
    remainder = sum_result % 11
    first_digit = 0 if remainder < 2 else 11 - remainder
    
    if int(cnpj[12]) != first_digit:
        return False
    
    # Calcula segundo dígito verificador
    weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_result = sum(int(cnpj[i]) * weights[i] for i in range(13))
    remainder = sum_result % 11
    second_digit = 0 if remainder < 2 else 11 - remainder
    
    return int(cnpj[13]) == second_digit

def validate_cpf(cpf: str) -> bool:
    """
    Valida CPF usando algoritmo oficial
    
    Args:
        cpf: String do CPF
        
    Returns:
        True se válido, False caso contrário
    """
    cpf = only_digits(cpf)
    
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Calcula primeiro dígito verificador
    sum_result = sum(int(cpf[i]) * (10 - i) for i in range(9))
    remainder = sum_result % 11
    first_digit = 0 if remainder < 2 else 11 - remainder
    
    if int(cpf[9]) != first_digit:
        return False
    
    # Calcula segundo dígito verificador
    sum_result = sum(int(cpf[i]) * (11 - i) for i in range(10))
    remainder = sum_result % 11
    second_digit = 0 if remainder < 2 else 11 - remainder
    
    return int(cpf[10]) == second_digit

def sanitize_filename(filename: str) -> str:
    """
    Sanitiza nome de arquivo removendo caracteres inválidos
    
    Args:
        filename: Nome do arquivo
        
    Returns:
        Nome sanitizado
    """
    # Remove caracteres inválidos para nomes de arquivo
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "_", filename)
    
    # Remove espaços extras e pontos no final
    sanitized = sanitized.strip().rstrip(".")
    
    # Limita tamanho
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    
    return sanitized

def get_file_size_str(file_path: Path) -> str:
    """
    Retorna tamanho do arquivo em formato legível
    
    Args:
        file_path: Caminho do arquivo
        
    Returns:
        String com tamanho formatado (ex: "1.5 MB")
    """
    try:
        size_bytes = file_path.stat().st_size
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        
        return f"{size_bytes:.1f} TB"
        
    except Exception as e:
        logger.warning(f"Erro ao obter tamanho do arquivo {file_path}: {e}")
        return "0 B"

def validate_nfe_key(key: str) -> bool:
    """
    Valida chave de NF-e (44 dígitos)
    
    Args:
        key: Chave da NF-e
        
    Returns:
        True se válida, False caso contrário
    """
    key = only_digits(key)
    
    if len(key) != 44:
        return False
    
    # Verifica se é composta apenas de dígitos
    if not key.isdigit():
        return False
    
    # TODO: Implementar validação completa do DV da chave
    # Por enquanto, apenas verifica se tem 44 dígitos
    
    return True

def extract_uf_from_key(key: str) -> str:
    """
    Extrai código da UF da chave da NF-e
    
    Args:
        key: Chave da NF-e (44 dígitos)
        
    Returns:
        Código da UF (2 dígitos) ou string vazia se inválida
    """
    key = only_digits(key)
    
    if len(key) == 44:
        return key[0:2]  # Primeiros 2 dígitos são o código da UF
    
    return ""

def extract_year_month_from_key(key: str) -> tuple[str, str]:
    """
    Extrai ano e mês da chave da NF-e
    
    Args:
        key: Chave da NF-e (44 dígitos)
        
    Returns:
        Tupla (ano, mês) ou ("", "") se inválida
    """
    key = only_digits(key)
    
    if len(key) == 44:
        year = "20" + key[2:4]  # Posições 2-3 são o ano (últimos 2 dígitos)
        month = key[4:6]        # Posições 4-5 são o mês
        return year, month
    
    return "", ""

def format_file_path(base_dir: Path, cnpj: str, year_month: str, filename: str) -> Path:
    """
    Formata caminho de arquivo seguindo estrutura padrão
    
    Args:
        base_dir: Diretório base
        cnpj: CNPJ (apenas dígitos)
        year_month: Ano-mês (YYYY-MM)
        filename: Nome do arquivo
        
    Returns:
        Path completo do arquivo
    """
    cnpj_digits = only_digits(cnpj)
    sanitized_filename = sanitize_filename(filename)
    
    return base_dir / cnpj_digits / year_month / sanitized_filename

def get_status_info(status: str) -> dict[str, str]:
    """
    Analisa status e retorna informações estruturadas
    
    Args:
        status: String do status
        
    Returns:
        Dicionário com tipo, cor e ícone sugeridos
    """
    status_lower = status.lower()
    
    if "autorizado" in status_lower or "confirmação da operação" in status_lower:
        return {
            "type": "success",
            "color": "#4caf50",
            "icon": "check_circle",
            "text": "Autorizado"
        }
    elif "cancelad" in status_lower:
        return {
            "type": "cancelled",
            "color": "#f44336",
            "icon": "cancel",
            "text": "Cancelado"
        }
    elif "rejeitad" in status_lower or "rejeição" in status_lower:
        return {
            "type": "rejected",
            "color": "#ff5722",
            "icon": "error",
            "text": "Rejeitado"
        }
    elif "denegad" in status_lower:
        return {
            "type": "denied",
            "color": "#e91e63",
            "icon": "block",
            "text": "Denegado"
        }
    else:
        return {
            "type": "pending",
            "color": "#ff9800",
            "icon": "schedule",
            "text": "Pendente"
        }

def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Trunca texto se exceder tamanho máximo
    
    Args:
        text: Texto a ser truncado
        max_length: Tamanho máximo
        suffix: Sufixo para indicar truncamento
        
    Returns:
        Texto truncado se necessário
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def parse_currency_to_float(currency_str: str) -> float:
    """
    Converte string de moeda para float
    
    Args:
        currency_str: String da moeda (ex: "R$ 1.234,56")
        
    Returns:
        Valor como float
    """
    try:
        # Remove símbolos e espaços
        clean_str = currency_str.replace("R$", "").strip()
        
        # Se tem vírgula e ponto, assume formato brasileiro
        if "," in clean_str and "." in clean_str:
            # Remove pontos (milhares) e troca vírgula por ponto (decimal)
            clean_str = clean_str.replace(".", "").replace(",", ".")
        elif "," in clean_str:
            # Apenas vírgula, assume decimal brasileiro
            clean_str = clean_str.replace(",", ".")
        
        return float(clean_str)
        
    except (ValueError, TypeError):
        return 0.0

def format_number(number: float, decimals: int = 2) -> str:
    """
    Formata número com separadores brasileiros
    
    Args:
        number: Número a ser formatado
        decimals: Número de casas decimais
        
    Returns:
        Número formatado
    """
    try:
        formatted = f"{number:,.{decimals}f}"
        # Converte para padrão brasileiro
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "0" + (",00" if decimals > 0 else "")