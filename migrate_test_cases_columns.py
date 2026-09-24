"""
Migration script: tambah kolom `action` dan `expected_result` ke tabel test_cases,
dan migrasikan data lama dari kolom `description` (kalau ada) ke `action`.

Cara pakai:
    cd dokumen-pengguna-be
    python migrations/migrate_test_cases_columns.py

Script ini aman dijalankan berkali-kali (idempotent) — dia cek dulu kolom mana
yang udah ada sebelum nambahin, jadi nggak akan error walau di-run ulang.

Yang dilakukan script ini, urut:
  1. Cek struktur tabel test_cases saat ini.
  2. Tambah kolom `action` (TEXT, default '') kalau belum ada.
  3. Tambah kolom `expected_result` (TEXT, default '') kalau belum ada.
  4. Kalau kolom lama `description` masih ada DAN masih ada isinya,
     copy isinya ke kolom `action` (supaya data lama nggak hilang).
  5. Kalau kolom lama `description` masih NOT NULL, diubah jadi nullable
     (supaya insert baru yang nggak isi `description` nggak gagal).
     Kolom `description` SENGAJA TIDAK di-drop di sini — biar kamu bisa
     cek dulu datanya udah kepindah bener sebelum beneran dihapus manual.
"""

import sys
import os

# Supaya bisa import `database` dari root folder backend
# meskipun script ini dijalankan dari dalam folder migrations/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text, inspect
from database import engine


def get_existing_columns(inspector, table_name: str) -> set:
    if table_name not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def main():
    inspector = inspect(engine)

    if "test_cases" not in inspector.get_table_names():
        print("❌ Tabel 'test_cases' tidak ditemukan di database. "
              "Pastikan model.TestCase sudah pernah di-create (Base.metadata.create_all() "
              "atau migration awal sudah jalan) sebelum menjalankan script ini.")
        return

    existing_columns = get_existing_columns(inspector, "test_cases")
    print(f"Kolom yang ada di 'test_cases' saat ini: {sorted(existing_columns)}")

    with engine.begin() as conn:
        # --- 1. Tambah kolom 'action' kalau belum ada ---
        if "action" not in existing_columns:
            print("➕ Menambahkan kolom 'action'...")
            conn.execute(text(
                "ALTER TABLE test_cases ADD COLUMN action TEXT NOT NULL DEFAULT ''"
            ))
        else:
            print("✓ Kolom 'action' sudah ada, dilewati.")

        # --- 2. Tambah kolom 'expected_result' kalau belum ada ---
        if "expected_result" not in existing_columns:
            print("➕ Menambahkan kolom 'expected_result'...")
            conn.execute(text(
                "ALTER TABLE test_cases ADD COLUMN expected_result TEXT NOT NULL DEFAULT ''"
            ))
        else:
            print("✓ Kolom 'expected_result' sudah ada, dilewati.")

        # --- 3. Migrasikan data lama dari 'description' ke 'action', kalau kolom lama masih ada ---
        if "description" in existing_columns:
            print("🔄 Kolom lama 'description' ditemukan, migrasi data ke 'action'...")
            result = conn.execute(text(
                """
                UPDATE test_cases
                SET action = description
                WHERE (action IS NULL OR action = '')
                  AND description IS NOT NULL
                  AND description <> ''
                """
            ))
            print(f"   {result.rowcount} baris berhasil dimigrasikan dari 'description' ke 'action'.")

            # --- 4. Pastikan 'description' nullable (supaya insert baru nggak gagal) ---
            print("🔓 Mengubah kolom 'description' jadi nullable (biar nggak block insert baru)...")
            conn.execute(text(
                "ALTER TABLE test_cases ALTER COLUMN description DROP NOT NULL"
            ))
            print("   Selesai. Kolom 'description' TIDAK dihapus otomatis — cek dulu datanya,")
            print("   baru drop manual kalau sudah yakin:")
            print("   ALTER TABLE test_cases DROP COLUMN description;")
        else:
            print("✓ Tidak ada kolom lama 'description' untuk dimigrasikan.")

    print("\n✅ Migration selesai.")


if __name__ == "__main__":
    main()