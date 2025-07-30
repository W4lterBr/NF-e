# db.py
import os
import sqlite3
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BANCO = os.path.join(SCRIPT_DIR, "notas.db")

def atualizar_schema_sqlite():
    conn = sqlite3.connect(BANCO)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS armazenamento (
            informante TEXT PRIMARY KEY,
            pasta TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS certificados (
            id INTEGER PRIMARY KEY,
            cnpj_cpf TEXT,
            caminho TEXT,
            senha TEXT,
            informante TEXT,
            cUF_autor TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS xmls_baixados (
            chave TEXT PRIMARY KEY,
            cnpj_cpf TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS nsu (
            informante TEXT PRIMARY KEY,
            ult_nsu TEXT
        )
    ''')
    conn.commit()
    conn.close()

def salvar_certificado(cnpj_cpf, caminho, senha, informante, cuf):
    conn = sqlite3.connect(BANCO)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO certificados (cnpj_cpf,caminho,senha,informante,cUF_autor) VALUES (?,?,?,?,?)",
        (cnpj_cpf, caminho, senha, informante, cuf)
    )
    conn.commit()
    conn.close()

def carregar_certificados():
    conn = sqlite3.connect(BANCO)
    cur = conn.cursor()
    cur.execute(
        "SELECT cnpj_cpf, caminho, senha, informante, cUF_autor FROM certificados"
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_ult_nsu(informante):
    conn = sqlite3.connect(BANCO)
    cur = conn.cursor()
    cur.execute("SELECT ult_nsu FROM nsu WHERE informante=?", (informante,))
    r = cur.fetchone()
    conn.close()
    return r[0] if r else '000000000000000'

def set_ult_nsu(informante, nsu):
    conn = sqlite3.connect(BANCO)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO nsu (informante,ult_nsu) VALUES (?,?)",
        (informante, nsu)
    )
    conn.commit()
    conn.close()

def registrar_xml_baixado(chave, cnpj_cpf):
    conn = sqlite3.connect(BANCO)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO xmls_baixados (chave,cnpj_cpf) VALUES (?,?)",
        (chave, cnpj_cpf)
    )
    conn.commit()
    conn.close()

def salvar_pasta_armazenamento(informante, pasta):
    conn = sqlite3.connect(BANCO)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO armazenamento (informante,pasta) VALUES (?,?)",
        (informante, pasta)
    )
    conn.commit()
    conn.close()

def obter_pasta_armazenamento(informante):
    conn = sqlite3.connect(BANCO)
    cur = conn.cursor()
    cur.execute("SELECT pasta FROM armazenamento WHERE informante=?", (informante,))
    r = cur.fetchone()
    conn.close()
    return r[0] if r else None
