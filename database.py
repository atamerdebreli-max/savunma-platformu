from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./savunma_platformu.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ==================== TABLOLAR ====================

# Değerlendirme tablosu
class Degerlendirme(Base):
    __tablename__ = "degerlendirmeler"

    id = Column(Integer, primary_key=True, index=True)
    sirket_adi = Column(String, index=True)
    kullanici_email = Column(String, index=True)
    cevaplar = Column(JSON)
    toplam_puan = Column(Integer)
    maksimum_puan = Column(Integer)
    yuzde = Column(Integer)
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)


# Kullanıcı tablosu
class Kullanici(Base):
    __tablename__ = "kullanicilar"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    sifre_hash = Column(String)
    sirket_adi = Column(String)
    rol = Column(String, default="kobi")
    plan = Column(String, default="ucretsiz")
    ai_kullanim_sayisi = Column(Integer, default=0)
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)


# Danışmanlık talepleri tablosu
class DanismanlikTalebi(Base):
    __tablename__ = "danismanlik_talepleri"

    id = Column(Integer, primary_key=True, index=True)
    sirket_adi = Column(String, index=True)
    email = Column(String)
    telefon = Column(String)
    mesaj = Column(String)
    durum = Column(String, default="beklemede")
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)


# Yol Haritası tablosu
class YolHaritasi(Base):
    __tablename__ = "yol_haritasi"

    id = Column(Integer, primary_key=True, index=True)
    kullanici_email = Column(String, index=True)
    adim_id = Column(String)
    tamamlandi = Column(Integer, default=0)
    tamamlanma_tarihi = Column(DateTime, default=datetime.utcnow)

# Hatırlatıcı tablosu
class Hatirlatici(Base):
    __tablename__ = "hatirlaticilar"

    id = Column(Integer, primary_key=True, index=True)
    kullanici_email = Column(String, index=True)
    baslik = Column(String)
    aciklama = Column(String)
    tarih = Column(String)  # YYYY-MM-DD formatında saklayacağız
    tip = Column(String)  # denetim, kalibrasyon, egitim, toplanti
    aktif = Column(Integer, default=1)
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)
    # Kalibrasyon tablosu
class Kalibrasyon(Base):
    __tablename__ = "kalibrasyonlar"

    id = Column(Integer, primary_key=True, index=True)
    kullanici_email = Column(String, index=True)
    ekipman_adi = Column(String)
    marka_model = Column(String)
    seri_no = Column(String)
    konum = Column(String)  # hangi departmanda
    son_kalibrasyon = Column(String)  # YYYY-MM-DD
    sonraki_kalibrasyon = Column(String)  # YYYY-MM-DD
    kalibrasyon_firmasi = Column(String)
    sertifika_no = Column(String)
    durum = Column(String, default="aktif")  # aktif, pasif
    notlar = Column(String, default="")
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)
    
# ==================== TABLOLARI OLUŞTUR ====================
Base.metadata.create_all(bind=engine)


# ==================== VERİTABANI OTURUMU ====================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()