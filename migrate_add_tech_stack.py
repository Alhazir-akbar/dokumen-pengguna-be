"""
Migration: tambah kolom-kolom baru ke tabel `tech_stacks` untuk menampung
jawaban wizard "Translate" (teknologi, ukuran software, database logic).

Cara pakai:
    1. Taruh file ini di root folder backend (sejajar dengan userdoc.db / main.py).
    2. Jalankan: python migrate_add_tech_stack_columns.py
    3. Aman dijalankan berkali-kali -- kolom yang sudah ada otomatis dilewati.

Kalau DATABASE_URL kamu bukan file default "./userdoc.db", ubah DB_PATH di
bawah, atau script ini akan otomatis coba baca dari .env kalau ada.
"""

import os
import sqlite3
import re

# ---- Cari path database ----
DEFAULT_DB_PATH = "userdoc.db"


def resolve_db_path() -> str:
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        match = re.search(r'DATABASE_URL\s*=\s*sqlite:///(.+)', content)
        if match:
            raw_path = match.group(1).strip().strip('"').strip("'")
            # sqlite:///./userdoc.db -> ./userdoc.db -> userdoc.db
            raw_path = raw_path.lstrip("./")
            return raw_path
    return DEFAULT_DB_PATH


DB_PATH = resolve_db_path()

# ---- Kolom baru yang mau ditambahkan (nama_kolom -> tipe SQLite) ----
NEW_COLUMNS = {
    "additional_technologies": "VARCHAR",
    "lines_of_code": "VARCHAR",
    "years_in_development": "VARCHAR",
    "size_class": "VARCHAR",
    "code_structure": "VARCHAR",
    "has_db_logic": "VARCHAR",
    "uses_microservices": "VARCHAR",
    "complexity_notes": "VARCHAR",
}

TABLE_NAME = "tech_stacks"


def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database tidak ditemukan di: {DB_PATH}")
        print("   Edit DB_PATH di script ini kalau lokasi file .db kamu berbeda.")
        return

    print(f"📂 Menggunakan database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Pastikan tabelnya ada
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE_NAME,),
    )
    if cursor.fetchone() is None:
        print(f"❌ Tabel '{TABLE_NAME}' tidak ditemukan di database ini.")
        conn.close()
        return

    # Ambil kolom yang sudah ada
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    existing_columns = {row[1] for row in cursor.fetchall()}

    added = []
    skipped = []

    for column_name, column_type in NEW_COLUMNS.items():
        if column_name in existing_columns:
            skipped.append(column_name)
            continue

        alter_sql = f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column_name} {column_type}"
        cursor.execute(alter_sql)
        added.append(column_name)

    conn.commit()
    conn.close()

    print()
    if added:
        print(f"✅ Kolom baru ditambahkan ({len(added)}):")
        for c in added:
            print(f"   + {c}")
    else:
        print("✅ Tidak ada kolom baru yang perlu ditambahkan.")

    if skipped:
        print(f"\nℹ️  Kolom yang sudah ada sebelumnya, dilewati ({len(skipped)}):")
        for c in skipped:
            print(f"   = {c}")

    print("\nSelesai. Restart server FastAPI kamu supaya model SQLAlchemy sinkron dengan skema baru.")


if __name__ == "__main__":
    main()