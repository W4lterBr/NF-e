from nfe_search import DatabaseManager

db = DatabaseManager('notas.db')
certs = db.get_certificados()

print("Estrutura da tupla de certificado:")
for idx, field in enumerate(certs[0]):
    val_str = str(field)[:50] if isinstance(field, str) else str(field)
    print(f"  [{idx}]: {val_str}")
