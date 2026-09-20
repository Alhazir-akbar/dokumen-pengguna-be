from sqlalchemy import inspect, text
from database import engine  # sesuaikan kalau nama file/module engine kamu beda

# Mapping tipe kolom SQLAlchemy -> tipe SQL Postgres yang dipakai saat ALTER TABLE
TYPE_MAP = {
    "VARCHAR": "VARCHAR",
    "INTEGER": "INTEGER",
    "DATETIME": "TIMESTAMP",
    "BOOLEAN": "BOOLEAN",
    "TEXT": "TEXT",
}

def sync_table(conn, inspector, table):
    table_name = table.name
    existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
    for column in table.columns:
        if column.name in existing_cols:
            continue
        col_type_str = str(column.type).split("(")[0].upper()
        sql_type = TYPE_MAP.get(col_type_str, "VARCHAR")
        stmt = f'ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS "{column.name}" {sql_type};'
        print(f"Running: {stmt}")
        conn.execute(text(stmt))

def main():
    import model  # pastikan semua class model ke-import supaya metadata lengkap

    inspector = inspect(engine)
    with engine.connect() as conn:
        for table_name, table in model.Base.metadata.tables.items():
            if not inspector.has_table(table_name):
                print(f"Tabel '{table_name}' belum ada di DB, skip (akan dibuat otomatis oleh create_all()).")
                continue
            sync_table(conn, inspector, table)
        conn.commit()

    print("\nSelesai! Semua kolom yang kurang sudah ditambahkan.")

if __name__ == "__main__":
    main()