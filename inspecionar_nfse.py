#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspeciona registros NFS-e no banco"""

import sqlite3
import json
from pathlib import Path

db_path = Path(__file__).parent / "notas.db"

with sqlite3.connect(db_path) as conn:
    cursor = conn.execute("""
        SELECT chave, numero, valor, xml_status, nome_emitente, data_emissao, status, nsu
        FROM notas_detalhadas 
        WHERE tipo LIKE '%NFS%'
        LIMIT 3
    """)
    
    columns = [d[0] for d in cursor.description]
    
    print("\n🔍 INSPEÇÃO DETALHADA DOS REGISTROS NFS-e:\n")
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"--- Registro {i} ---")
        data = dict(zip(columns, row))
        for k, v in data.items():
            print(f"  {k}: {repr(v)}")
        print()
