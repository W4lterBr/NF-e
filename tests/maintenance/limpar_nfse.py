#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Limpa NFS-e com dados incorretos"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "notas.db"

with sqlite3.connect(db_path) as conn:
    cursor = conn.execute("DELETE FROM notas_detalhadas WHERE tipo LIKE '%NFS%'")
    count = cursor.rowcount
    conn.commit()
    print(f"✅ {count} NFS-e removidas do banco")
    print("\n💡 Execute novamente: python buscar_nfse_auto.py")
