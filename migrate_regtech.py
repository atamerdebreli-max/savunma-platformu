"""
RegTech tablolarına assessment_tipi kolonu ekler.
SQLite ve PostgreSQL uyumludur.
Çalıştırma: python migrate_regtech.py
"""
from sqlalchemy import text, inspect
from database import engine

def sutun_var_mi(conn, tablo_adi, sutun_adi):
    """Sütunun tabloda var olup olmadığını kontrol eder."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(tablo_adi)]
    return sutun_adi in columns

def main():
    print("🔧 Migration başlıyor...")
    with engine.connect() as conn:
        # regtech_sorulari tablosuna assessment_tipi ekle
        try:
            if not sutun_var_mi(conn, 'regtech_sorulari', 'assessment_tipi'):
                conn.execute(text(
                    "ALTER TABLE regtech_sorulari "
                    "ADD COLUMN assessment_tipi VARCHAR DEFAULT 'farkindalik'"
                ))
                print("✅ regtech_sorulari.assessment_tipi eklendi")
            else:
                print("⏩ regtech_sorulari.assessment_tipi zaten var")
        except Exception as e:
            print(f"⚠️ regtech_sorulari: {e}")

        # regtech_assessments tablosuna assessment_tipi ekle
        try:
            if not sutun_var_mi(conn, 'regtech_assessments', 'assessment_tipi'):
                conn.execute(text(
                    "ALTER TABLE regtech_assessments "
                    "ADD COLUMN assessment_tipi VARCHAR DEFAULT 'farkindalik'"
                ))
                print("✅ regtech_assessments.assessment_tipi eklendi")
            else:
                print("⏩ regtech_assessments.assessment_tipi zaten var")
        except Exception as e:
            print(f"⚠️ regtech_assessments: {e}")

        conn.commit()
        print("\n🎉 Migration tamamlandı!")

if __name__ == "__main__":
    main()