from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE user_stories ADD COLUMN IF NOT EXISTS labels VARCHAR;
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS story_links (
            id SERIAL PRIMARY KEY,
            source_story_id INTEGER NOT NULL REFERENCES user_stories(id),
            target_story_id INTEGER NOT NULL REFERENCES user_stories(id),
            link_type VARCHAR NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """))

    conn.commit()

print("Migrasi selesai: kolom labels & tabel story_links siap.")