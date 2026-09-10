"""
Migrasi sekali-jalan untuk menambahkan kolom-kolom baru Build Module
(Technology Stack, Coding Guidelines, Development Plans) ke database SQLite
yang sudah ada, tanpa menghapus data lama.

CARA PAKAI:
1. Taruh file ini di root project backend (folder yang sama dengan main.py / database.py),
   sejajar dengan file .db kamu.
2. Sesuaikan DB_PATH di bawah kalau nama/lokasi file .db kamu berbeda dari default.
3. Jalankan:  python migrate_build_module.py
4. Restart server uvicorn-nya setelah migrasi selesai.

Script ini AMAN dijalankan berkali-kali -- setiap kolom dicek dulu apakah sudah
ada sebelum di-ALTER, jadi tidak akan error "duplicate column" kalau dijalankan ulang.
"""

import sqlite3
import os
import sys
import glob

# TAMBAHAN: Ganti path ini kalau nama file database kamu berbeda.
# Kalau tidak yakin namanya apa, biarkan None -- script akan mencoba menebak
# otomatis dengan mencari file *.db / *.sqlite3 di folder saat ini.
DB_PATH = None


def find_db_path() -> str:
    if DB_PATH and os.path.exists(DB_PATH):
        return DB_PATH

    candidates = glob.glob("*.db") + glob.glob("*.sqlite3") + glob.glob("*.sqlite")
    if not candidates:
        print("Tidak menemukan file database (.db/.sqlite3/.sqlite) di folder ini.")
        print("Set variabel DB_PATH di bagian atas file ini secara manual, lalu jalankan lagi.")
        sys.exit(1)

    if len(candidates) > 1:
        print("Ditemukan beberapa file database, pilih salah satu:")
        for i, c in enumerate(candidates):
            print(f"  [{i}] {c}")
        idx = input("Masukkan nomor: ").strip()
        return candidates[int(idx)]

    print(f"Menggunakan database: {candidates[0]}")
    return candidates[0]


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def add_column_if_missing(cursor: sqlite3.Cursor, table: str, column: str, col_type: str):
    if column_exists(cursor, table, column):
        print(f"  - {table}.{column} sudah ada, skip.")
        return
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    print(f"  + {table}.{column} ({col_type}) ditambahkan.")


def main():
    db_path = find_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n== tech_stacks ==")
    add_column_if_missing(cursor, "tech_stacks", "target_users", "VARCHAR")
    add_column_if_missing(cursor, "tech_stacks", "scale", "VARCHAR")
    add_column_if_missing(cursor, "tech_stacks", "platform", "VARCHAR")
    add_column_if_missing(cursor, "tech_stacks", "ui_language", "VARCHAR")
    add_column_if_missing(cursor, "tech_stacks", "ui_framework", "VARCHAR")
    add_column_if_missing(cursor, "tech_stacks", "ui_library", "VARCHAR")
    add_column_if_missing(cursor, "tech_stacks", "app_language", "VARCHAR")
    add_column_if_missing(cursor, "tech_stacks", "app_framework", "VARCHAR")
    # data_layer, integration_layer, ui_layer, app_layer, updated_at seharusnya
    # sudah ada dari skema lama -- tidak perlu ditambahkan lagi.

    print("\n== coding_guidelines ==")
    add_column_if_missing(cursor, "coding_guidelines", "category", "VARCHAR")
    add_column_if_missing(cursor, "coding_guidelines", "updated_at", "DATETIME")

    print("\n== development_plans ==")
    add_column_if_missing(cursor, "development_plans", "epic_id", "INTEGER")
    add_column_if_missing(cursor, "development_plans", "updated_at", "DATETIME")

    conn.commit()
    conn.close()
    print("\nMigrasi selesai. Sekarang restart server uvicorn/FastAPI-nya.")


if __name__ == "__main__":
    main()