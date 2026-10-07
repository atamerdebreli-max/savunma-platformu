from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Float, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./savunma_platformu.db")

# PostgreSQL için check_same_thread gerekmez
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

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


# ==================== UZMAN DANIŞMAN AĞI ====================

# Uzman tablosu
class Uzman(Base):
    __tablename__ = "uzmanlar"

    id = Column(Integer, primary_key=True, index=True)
    ad_soyad = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    telefon = Column(String, default="")
    uzmanlik_alani = Column(String)  # FAI, FOD, YETEN, AS9100, EYDEP
    deneyim_yili = Column(Integer, default=0)
    sertifikalar = Column(Text, default="")
    referanslar = Column(Text, default="")
    fiyat_araligi = Column(String, default="")
    sehir = Column(String, default="")
    profil_fotografi = Column(String, default="")
    onay_durumu = Column(String, default="beklemede")  # beklemede, onayli, reddedildi
    puan = Column(Float, default=0)
    toplam_is = Column(Integer, default=0)
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)


# Randevu tablosu
class Randevu(Base):
    __tablename__ = "randevular"

    id = Column(Integer, primary_key=True, index=True)
    kobi_email = Column(String, index=True)
    uzman_id = Column(Integer, ForeignKey("uzmanlar.id"))
    hizmet_turu = Column(String)  # FAI egitimi, FOD egitimi, YETEN destegi
    tarih = Column(String)
    saat = Column(String)
    durum = Column(String, default="beklemede")  # beklemede, onaylandi, tamamlandi, iptal
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)


# Uzman Ödeme tablosu
class UzmanOdeme(Base):
    __tablename__ = "uzman_odemeler"

    id = Column(Integer, primary_key=True, index=True)
    randevu_id = Column(Integer, ForeignKey("randevular.id"))
    tutar = Column(Float)
    komisyon_orani = Column(Float, default=15.0)
    komisyon_tutari = Column(Float)
    iyzico_islem_id = Column(String, default="")
    odeme_durumu = Column(String, default="beklemede")
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)


# Uzman Yorum tablosu
class UzmanYorum(Base):
    __tablename__ = "uzman_yorumlar"

    id = Column(Integer, primary_key=True, index=True)
    randevu_id = Column(Integer, ForeignKey("randevular.id"))
    kobi_email = Column(String, index=True)
    uzman_id = Column(Integer, ForeignKey("uzmanlar.id"))
    puan = Column(Integer)  # 1-5
    yorum = Column(Text, default="")
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)


# ==================== TABLOLARI OLUŞTUR ====================
Base.metadata.create_all(bind=engine)

# ==================== ANA YÜKLENİCİ MODÜLÜ ====================

class AnaYuklenici(Base):
    __tablename__ = "ana_yukleniciler"

    id = Column(Integer, primary_key=True, index=True)
    sirket_adi = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    sifre_hash = Column(String)
    yetkili_adi = Column(String, default="")
    telefon = Column(String, default="")
    website = Column(String, default="")
    logo_url = Column(String, default="")
    onay_durumu = Column(String, default="beklemede")  # beklemede, onayli, reddedildi
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)
# ==================== VERİTABANI OTURUMU ====================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()