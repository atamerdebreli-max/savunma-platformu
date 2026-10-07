import requests
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict, List

from database import (
    Degerlendirme, Kullanici, DanismanlikTalebi, YolHaritasi,
    Hatirlatici, Kalibrasyon, get_db, SessionLocal,
    Uzman, Randevu, UzmanOdeme, UzmanYorum
)
from auth import (
    sifre_hashle, sifre_dogrula, token_olustur,
    mevcut_kullanici, oauth2_scheme
)

import smtplib
import os
import io
import json
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
import docx
import iyzipay
from database import (
    Degerlendirme, Kullanici, DanismanlikTalebi, YolHaritasi,
    Hatirlatici, Kalibrasyon, get_db, SessionLocal,
    Uzman, Randevu, UzmanOdeme, UzmanYorum,
    AnaYuklenici, Egitim, EgitimSoru, EgitimIlerleme
)
from database import (
    Degerlendirme, Kullanici, DanismanlikTalebi, YolHaritasi,
    Hatirlatici, Kalibrasyon, get_db, SessionLocal,
    Uzman, Randevu, UzmanOdeme, UzmanYorum,
    AnaYuklenici
)
from database import (
    Degerlendirme, Kullanici, DanismanlikTalebi, YolHaritasi,
    Hatirlatici, Kalibrasyon, get_db, SessionLocal,
    Uzman, Randevu, UzmanOdeme, UzmanYorum,
    AnaYuklenici, Egitim, EgitimSoru, EgitimIlerleme,
    YETENBilgi
)
load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# iyzico istemcisi (Sandbox test modu)
iyzico_options = {
    'api_key': os.getenv("IYZICO_API_KEY"),
    'secret_key': os.getenv("IYZICO_SECRET_KEY"),
    'base_url': os.getenv("IYZICO_BASE_URL")
}

# ==================== E-POSTA FONKSİYONU ====================

def email_gonder(konu: str, icerik: str):
    try:
        api_key = os.getenv("RESEND_API_KEY")
        alici = os.getenv("BILDIRIM_ALICISI")
        
        if not api_key or not alici:
            print("E-posta ayarları eksik.")
            return False
        
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "from": "UyumOS <onboarding@resend.dev>",
                "to": [alici],
                "subject": konu,
                "text": icerik
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"E-posta gönderildi: {konu}")
            return True
        else:
            print(f"E-posta hatası: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"E-posta hatası: {e}")
        return False
# ==================== FASTAPI ====================

app = FastAPI(
    title="UyumOS",
    description="KOBİ'ler için Uyumluluk İşletim Sistemi",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== VERİ MODELLERİ ====================

class DegerlendirmeGirdi(BaseModel):
    sirket_adi: str
    kullanici_email: str = ""
    cevaplar: Dict[str, int]

class KullaniciKayit(BaseModel):
    email: str
    sifre: str
    sirket_adi: str

class DanismanlikTalepGirdi(BaseModel):
    sirket_adi: str
    email: str
    telefon: str
    mesaj: str = ""

class AdminYapGirdi(BaseModel):
    email: str

class DenetimMesajGirdi(BaseModel):
    mesajlar: List[Dict[str, str]]
    sirket_adi: str = ""

class SablonWordGirdi(BaseModel):
    baslik: str
    icerik_html: str

class HatirlaticiGirdi(BaseModel):
    kullanici_email: str
    baslik: str
    aciklama: str = ""
    tarih: str
    tip: str = "denetim"

class KalibrasyonGirdi(BaseModel):
    kullanici_email: str
    ekipman_adi: str
    marka_model: str = ""
    seri_no: str = ""
    konum: str = ""
    son_kalibrasyon: str = ""
    sonraki_kalibrasyon: str
    kalibrasyon_firmasi: str = ""
    sertifika_no: str = ""
    notlar: str = ""


# ==================== TEMEL ====================

@app.get("/")
def ana_sayfa():
    return {"mesaj": "UyumOS API'si", "durum": "çalışıyor"}

@app.get("/saglik")
def saglik():
    return {"durum": "sağlıklı"}


# ==================== KULLANICI ====================

@app.post("/kayit")
def kayit(girdi: KullaniciKayit, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    mevcut = db.query(Kullanici).filter(Kullanici.email == girdi.email).first()
    if mevcut:
        raise HTTPException(status_code=400, detail="Bu email zaten kayıtlı")

    yeni = Kullanici(
        email=girdi.email,
        sifre_hash=sifre_hashle(girdi.sifre),
        sirket_adi=girdi.sirket_adi,
        rol="kobi",
        plan="ucretsiz"
    )
    db.add(yeni)
    db.commit()
    db.refresh(yeni)

    # Email'i arka planda gönder (kayıt bloke olmasın)
    background_tasks.add_task(
        email_gonder,
        konu=f"Yeni Kayıt: {girdi.sirket_adi}",
        icerik=f"Yeni KOBİ kayıt oldu!\n\nŞirket: {girdi.sirket_adi}\nE-posta: {girdi.email}\n"
    )

    return {
        "mesaj": "Kullanıcı kaydedildi",
        "kullanici": {
            "id": yeni.id, "email": yeni.email,
            "sirket_adi": yeni.sirket_adi, "rol": yeni.rol, "plan": yeni.plan
        }
    }
@app.post("/giris")
def giris(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    kullanici = db.query(Kullanici).filter(Kullanici.email == form_data.username).first()
    if not kullanici or not sifre_dogrula(form_data.password, kullanici.sifre_hash):
        raise HTTPException(status_code=401, detail="Email veya şifre hatalı")
    
    token = token_olustur(data={"sub": kullanici.email, "rol": kullanici.rol})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "kullanici": {
            "id": kullanici.id, "email": kullanici.email,
            "sirket_adi": kullanici.sirket_adi, "rol": kullanici.rol, "plan": kullanici.plan
        }
    }

@app.get("/ben")
def ben(kullanici: Kullanici = Depends(mevcut_kullanici)):
    return {
        "id": kullanici.id, "email": kullanici.email,
        "sirket_adi": kullanici.sirket_adi, "rol": kullanici.rol, "plan": kullanici.plan
    }


# ==================== PLAN ====================

@app.get("/plan-bilgisi")
def plan_bilgisi(email: str, db: Session = Depends(get_db)):
    kullanici = db.query(Kullanici).filter(Kullanici.email == email).first()
    if not kullanici:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    assessment_sayisi = db.query(Degerlendirme).filter(
        Degerlendirme.kullanici_email == email
    ).count()
    
    limitler = {
        "ucretsiz": {"ad": "Ücretsiz", "assessment": 1, "ai": 0},
        "temel": {"ad": "Temel", "assessment": 5, "ai": 0},
        "profesyonel": {"ad": "Profesyonel", "assessment": 999999, "ai": 5},
        "kurumsal": {"ad": "Kurumsal", "assessment": 999999, "ai": 999999}
    }
    limit = limitler.get(kullanici.plan, limitler["ucretsiz"])
    
    return {
        "plan": kullanici.plan, "plan_adi": limit["ad"],
        "assessment_kullanim": assessment_sayisi, "assessment_limit": limit["assessment"],
        "ai_kullanim": kullanici.ai_kullanim_sayisi, "ai_limit": limit["ai"]
    }


# ==================== DEĞERLENDİRME ====================

@app.post("/degerlendirme")
def degerlendirme_kaydet(girdi: DegerlendirmeGirdi, db: Session = Depends(get_db)):
    if girdi.kullanici_email:
        kullanici = db.query(Kullanici).filter(Kullanici.email == girdi.kullanici_email).first()
        if kullanici:
            mevcut = db.query(Degerlendirme).filter(
                Degerlendirme.kullanici_email == girdi.kullanici_email
            ).count()
            limit = {"ucretsiz": 1, "temel": 5, "profesyonel": 999999, "kurumsal": 999999}
            if mevcut >= limit.get(kullanici.plan, 1):
                raise HTTPException(status_code=403, detail=f"Assessment limitinize ulaştınız. Planınızı yükseltin.")
    
    toplam = sum(girdi.cevaplar.values())
    maks = len(girdi.cevaplar) * 10
    yuzde = round((toplam / maks) * 100) if maks > 0 else 0
    
    yeni = Degerlendirme(
        sirket_adi=girdi.sirket_adi,
        kullanici_email=girdi.kullanici_email,
        cevaplar=girdi.cevaplar,
        toplam_puan=toplam, maksimum_puan=maks, yuzde=yuzde
    )
        # EYDEP seviyesini güncelle
    if girdi.kullanici_email:
        kullanici = db.query(Kullanici).filter(Kullanici.email == girdi.kullanici_email).first()
        if kullanici:
            kullanici.eydep_seviye = eydep_seviye_hesapla(yuzde)
            kullanici.eydep_skor = yuzde
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    
    return {
        "mesaj": "Değerlendirme kaydedildi",
        "kayit": {
            "id": yeni.id, "sirket_adi": yeni.sirket_adi,
            "kullanici_email": yeni.kullanici_email,
            "cevaplar": yeni.cevaplar,
            "toplam_puan": yeni.toplam_puan, "maksimum_puan": yeni.maksimum_puan,
            "yuzde": yeni.yuzde, "olusturma_tarihi": yeni.olusturma_tarihi.isoformat()
        }
    }

@app.get("/degerlendirmeler")
def tum_degerlendirmeler(db: Session = Depends(get_db)):
    kayitlar = db.query(Degerlendirme).order_by(Degerlendirme.olusturma_tarihi.desc()).all()
    return {
        "toplam": len(kayitlar),
        "kayitlar": [{
            "id": k.id, "sirket_adi": k.sirket_adi,
            "kullanici_email": k.kullanici_email,
            "toplam_puan": k.toplam_puan, "maksimum_puan": k.maksimum_puan,
            "yuzde": k.yuzde, "olusturma_tarihi": k.olusturma_tarihi.isoformat()
        } for k in kayitlar]
    }

@app.get("/kullanicinin-degerlendirmeleri")
def kullanicinin_degerlendirmeleri(email: str, db: Session = Depends(get_db)):
    kayitlar = db.query(Degerlendirme).filter(
        Degerlendirme.kullanici_email == email
    ).order_by(Degerlendirme.olusturma_tarihi.desc()).all()
    return {
        "toplam": len(kayitlar),
        "kayitlar": [{
            "id": k.id, "sirket_adi": k.sirket_adi,
            "toplam_puan": k.toplam_puan, "maksimum_puan": k.maksimum_puan,
            "yuzde": k.yuzde, "olusturma_tarihi": k.olusturma_tarihi.isoformat()
        } for k in kayitlar]
    }

@app.delete("/degerlendirme/{kayit_id}")
def degerlendirme_sil(kayit_id: int, db: Session = Depends(get_db)):
    kayit = db.query(Degerlendirme).filter(Degerlendirme.id == kayit_id).first()
    if not kayit:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
    db.delete(kayit)
    db.commit()
    return {"mesaj": f"Kayıt {kayit_id} silindi"}


# ==================== DANIŞMANLIK ====================

@app.post("/danismanlik-talebi")
def danismanlik_talebi(girdi: DanismanlikTalepGirdi, db: Session = Depends(get_db)):
    yeni = DanismanlikTalebi(
        sirket_adi=girdi.sirket_adi, email=girdi.email,
        telefon=girdi.telefon, mesaj=girdi.mesaj
    )
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    
    email_gonder(
        konu=f"YENİ DANIŞMANLIK TALEBİ: {girdi.sirket_adi}",
        icerik=f"Şirket: {girdi.sirket_adi}\nE-posta: {girdi.email}\nTelefon: {girdi.telefon}\nMesaj: {girdi.mesaj or '—'}\n"
    )
    
    return {"mesaj": "Danışmanlık talebiniz alındı.", "talep_id": yeni.id}

@app.get("/danismanlik-talepleri")
def danismanlik_listele(db: Session = Depends(get_db)):
    talepler = db.query(DanismanlikTalebi).order_by(DanismanlikTalebi.olusturma_tarihi.desc()).all()
    return {
        "toplam": len(talepler),
        "talepler": [{
            "id": t.id, "sirket_adi": t.sirket_adi, "email": t.email,
            "telefon": t.telefon, "mesaj": t.mesaj, "durum": t.durum,
            "olusturma_tarihi": t.olusturma_tarihi.isoformat()
        } for t in talepler]
    }


# ==================== ADMIN ====================

@app.post("/admin-yap")
def admin_yap(girdi: AdminYapGirdi, db: Session = Depends(get_db)):
    kullanici = db.query(Kullanici).filter(Kullanici.email == girdi.email).first()
    if not kullanici:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    kullanici.rol = "admin"
    db.commit()
    return {"mesaj": f"{girdi.email} artık admin", "rol": kullanici.rol}

@app.post("/plan-degistir")
def plan_degistir(email: str, yeni_plan: str, db: Session = Depends(get_db)):
    kullanici = db.query(Kullanici).filter(Kullanici.email == email).first()
    if not kullanici:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    if yeni_plan not in ["ucretsiz", "temel", "profesyonel", "kurumsal"]:
        raise HTTPException(status_code=400, detail="Geçersiz plan")
    kullanici.plan = yeni_plan
    db.commit()
    return {"mesaj": f"{email} planı {yeni_plan} olarak güncellendi", "plan": yeni_plan}

@app.get("/admin/ozet")
def admin_ozet(db: Session = Depends(get_db)):
    return {
        "toplam_kullanici": db.query(Kullanici).count(),
        "toplam_assessment": db.query(Degerlendirme).count(),
        "toplam_talep": db.query(DanismanlikTalebi).count(),
        "bekleyen_talep": db.query(DanismanlikTalebi).filter(DanismanlikTalebi.durum == "beklemede").count()
    }

@app.get("/admin/kullanicilar")
def admin_kullanicilar(db: Session = Depends(get_db)):
    kullanicilar = db.query(Kullanici).order_by(Kullanici.olusturma_tarihi.desc()).all()
    return {
        "toplam": len(kullanicilar),
        "kullanicilar": [{
            "id": k.id, "email": k.email, "sirket_adi": k.sirket_adi,
            "rol": k.rol, "plan": k.plan, "ai_kullanim_sayisi": k.ai_kullanim_sayisi,
            "olusturma_tarihi": k.olusturma_tarihi.isoformat()
        } for k in kullanicilar]
    }

@app.get("/admin/tum-assessmentlar")
def admin_tum_assessmentlar(db: Session = Depends(get_db)):
    kayitlar = db.query(Degerlendirme).order_by(Degerlendirme.olusturma_tarihi.desc()).all()
    return {
        "toplam": len(kayitlar),
        "kayitlar": [{
            "id": k.id, "sirket_adi": k.sirket_adi,
            "kullanici_email": k.kullanici_email,
            "toplam_puan": k.toplam_puan, "maksimum_puan": k.maksimum_puan,
            "yuzde": k.yuzde, "olusturma_tarihi": k.olusturma_tarihi.isoformat()
        } for k in kayitlar]
    }

@app.put("/admin/talep-durum/{talep_id}")
def admin_talep_durum(talep_id: int, yeni_durum: str, db: Session = Depends(get_db)):
    talep = db.query(DanismanlikTalebi).filter(DanismanlikTalebi.id == talep_id).first()
    if not talep:
        raise HTTPException(status_code=404, detail="Talep bulunamadı")
    talep.durum = yeni_durum
    db.commit()
    return {"mesaj": "Durum güncellendi", "durum": yeni_durum}


# ==================== GAP ANALİZİ ====================

KATEGORILER = {
    "kategori1": {"ad": "Kalite Yönetim Sistemi", "sorular": list(range(1, 11))},
    "kategori2": {"ad": "Üretim Altyapısı", "sorular": list(range(11, 21))},
    "kategori3": {"ad": "İzlenebilirlik", "sorular": list(range(21, 31))},
    "kategori4": {"ad": "İnsan Kaynağı", "sorular": list(range(31, 41))},
    "kategori5": {"ad": "Tasarım ve Ar-Ge", "sorular": list(range(41, 51))},
    "kategori6": {"ad": "Kurumsallaşma", "sorular": list(range(51, 61))},
    "kategori7": {"ad": "Tedarikçi Yönetimi", "sorular": list(range(61, 71))},
}

SORU_METINLERI = {
    1: "Yazılı kalite politikası", 2: "Yazılı ve ölçülebilir kalite hedefleri",
    3: "Güncel kalite el kitabı", 4: "Doküman kontrol prosedürü",
    5: "Kayıt kontrol prosedürü", 6: "Yönetim gözden geçirme toplantıları",
    7: "İç denetim prosedürü", 8: "Düzeltici faaliyet prosedürü",
    9: "Önleyici faaliyet prosedürü", 10: "Kalite kayıtlarının saklanması",
    11: "Makine parkı listesi ve kapasitesi", 12: "Planlı bakım programı",
    13: "Ölçüm ekipmanlarının kalibrasyonu", 14: "Yazılı üretim kapasitesi planı",
    15: "Yazılı üretim süreç prosedürleri", 16: "Yazılı iş talimatları",
    17: "Özel süreç parametre kayıtları", 18: "İlk parça muayenesi (FAI)",
    19: "Üretim ortamı kontrolü", 20: "Yabancı madde (FOD) önleme politikası",
    21: "Hammadde-sevkiyat izlenebilirliği", 22: "Parti/lot numarası takibi",
    23: "Hammadde sertifikalarının saklanması", 24: "Üretim parametrelerinin kaydı",
    25: "Parça-makine eşleştirmesi", 26: "Ölçüm sonuçlarının kaydı",
    27: "Kalibrasyon kayıtlarının izlenebilirliği", 28: "Personel yetkinlik kayıtları",
    29: "Müşteri şikayetlerinin kaydı", 30: "Sevkiyat sonrası geri bildirim",
    31: "Personel yetkinlik belgeleri", 32: "Yıllık eğitim planı",
    33: "Eğitim kayıtları", 34: "Yazılı iş tanımları",
    35: "Kritik pozisyon yedek planı", 36: "Çalışan memnuniyeti ölçümü",
    37: "İş güvenliği eğitimleri", 38: "Operatör sertifikaları",
    39: "Personel devir hızı takibi", 40: "Kalite farkındalığı eğitimi",
    41: "Yazılı tasarım prosedürü", 42: "Tasarım girdilerinin toplanması",
    43: "Tasarım çıktılarının gözden geçirilmesi", 44: "Tasarım değişiklik kontrolü",
    45: "Tasarım doğrulama ve geçerli kılma", 46: "Ar-Ge bütçesi",
    47: "Tasarım risk analizi (FMEA)", 48: "Yetkin tasarım ekibi",
    49: "Müşteriyle tasarım gözden geçirme", 50: "Tasarım kayıtlarının arşivlenmesi",
    51: "Yazılı organizasyon şeması", 52: "Yazılı görev ve sorumluluklar",
    53: "Düzenli yönetim gözden geçirme", 54: "Yazılı stratejik plan",
    55: "Tanımlı iç iletişim kanalları", 56: "Kalite politikasının duyurulması",
    57: "Müşteri memnuniyeti ölçümü", 58: "Yasal şartların takibi",
    59: "Etik davranış politikası", 60: "Süreç performansı ölçümü (KPI)",
    61: "Onaylı tedarikçi listesi", 62: "Yazılı tedarikçi seçim kriterleri",
    63: "Tedarikçi değerlendirmesi", 64: "Tedarikçi kalite belgeleri",
    65: "Hammadde giriş kontrolü", 66: "Tedarikçi sertifikalarının saklanması",
    67: "Alt tedarikçi performans ölçümü", 68: "Tedarikçi şikayet kaydı",
    69: "Tedarikçi denetimi", 70: "Sahte parça önleme politikası",
}

@app.get("/gap-analizi/{kayit_id}")
def gap_analizi(kayit_id: int, db: Session = Depends(get_db)):
    kayit = db.query(Degerlendirme).filter(Degerlendirme.id == kayit_id).first()
    if not kayit:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
    
    cevaplar = kayit.cevaplar
    kategori_sonuclari = []
    kritik_eksikler = []
    
    for kat_key, kat_bilgi in KATEGORILER.items():
        kat_puan = 0
        kat_max = 0
        kat_eksikler = []
        
        for soru_no in kat_bilgi["sorular"]:
            puan = cevaplar.get(f"soru{soru_no}", 0)
            kat_puan += puan
            kat_max += 10
            if puan == 0:
                kat_eksikler.append({
                    "soru_no": soru_no,
                    "metin": SORU_METINLERI.get(soru_no, f"Soru {soru_no}")
                })
                kritik_eksikler.append({
                    "kategori": kat_bilgi["ad"], "soru_no": soru_no,
                    "metin": SORU_METINLERI.get(soru_no, f"Soru {soru_no}")
                })
        
        kat_yuzde = round((kat_puan / kat_max) * 100) if kat_max > 0 else 0
        durum = "İyi" if kat_yuzde >= 70 else ("Orta" if kat_yuzde >= 40 else "Zayıf")
        renk = "yesil" if kat_yuzde >= 70 else ("sari" if kat_yuzde >= 40 else "kirmizi")
        
        kategori_sonuclari.append({
            "kategori": kat_bilgi["ad"], "puan": kat_puan,
            "maksimum": kat_max, "yuzde": kat_yuzde,
            "durum": durum, "renk": renk, "eksikler": kat_eksikler
        })
    
    return {
        "sirket_adi": kayit.sirket_adi, "kayit_id": kayit.id,
        "toplam_puan": kayit.toplam_puan, "maksimum_puan": kayit.maksimum_puan,
        "genel_yuzde": kayit.yuzde, "kategoriler": kategori_sonuclari,
        "kritik_eksikler": kritik_eksikler,
        "kritik_eksik_sayisi": len(kritik_eksikler)
    }


# ==================== AI DOKÜMAN TARAMA ====================

@app.post("/dokuman-tara")
async def dokuman_tara(
    dosya: UploadFile = File(...),
    sirket_adi: str = Form(""),
    kullanici_email: str = Form("")
):
    db = SessionLocal()
    if kullanici_email:
        kullanici = db.query(Kullanici).filter(Kullanici.email == kullanici_email).first()
        if kullanici:
            if kullanici.plan in ["ucretsiz", "temel"]:
                db.close()
                return {"basarili": False, "hata": "AI tarama sadece Profesyonel ve Kurumsal planlarda kullanılabilir."}
            if kullanici.plan == "profesyonel" and kullanici.ai_kullanim_sayisi >= 5:
                db.close()
                return {"basarili": False, "hata": "Aylık AI limitinize ulaştınız (5/5)."}
            kullanici.ai_kullanim_sayisi += 1
            db.commit()
    db.close()
    
    try:
        icerik = await dosya.read()
        dosya_adi = dosya.filename.lower()
        metin = ""
        
        if dosya_adi.endswith('.pdf'):
            reader = PdfReader(io.BytesIO(icerik))
            for sayfa in reader.pages:
                metin += sayfa.extract_text() + "\n"
        elif dosya_adi.endswith('.docx'):
            doc = docx.Document(io.BytesIO(icerik))
            for p in doc.paragraphs:
                metin += p.text + "\n"
        elif dosya_adi.endswith('.txt'):
            metin = icerik.decode('utf-8', errors='ignore')
        else:
            return {"basarili": False, "hata": "Desteklenmeyen dosya tipi. PDF, DOCX, TXT kabul edilir."}
        
        if len(metin) > 30000:
            metin = metin[:30000] + "\n\n[... metin kısaltıldı ...]"
        
        if not metin.strip():
            return {"basarili": False, "hata": "Dosyadan metin okunamadı."}
        
        prompt = f"""AS9100 kalite yönetim sistemi uzmanısın. Aşağıdaki dokümanı analiz et.

DOKÜMAN:
{metin}

Yanıtını SADECE şu JSON formatında ver:
{{
  "genel_ozet": "2-3 cümle değerlendirme",
  "bulunanlar": ["Bulunan 1", "Bulunan 2"],
  "eksikler": ["Eksik 1", "Eksik 2"],
  "oneriler": ["Öneri 1", "Öneri 2"],
  "as9100_uygunluk_skoru": 65
}}"""
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "AS9100 uzmanısın. Türkçe ve JSON formatında cevap ver."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        sonuc = json.loads(response.choices[0].message.content)
        return {"basarili": True, "dosya_adi": dosya.filename, "sirket_adi": sirket_adi, "sonuc": sonuc}
        
    except Exception as e:
        return {"basarili": False, "hata": f"Analiz edilemedi: {str(e)}"}


# ==================== YOL HARİTASI ====================

YOL_HARITASI_ADIMLARI = [
    {"id": "adim1", "asama": "Aşama 1: Eksikleri Kapat", "baslik": "Risk yönetimi prosedürü yaz", "aciklama": "Yazılı bir risk yönetimi prosedürü oluşturun."},
    {"id": "adim2", "asama": "Aşama 1: Eksikleri Kapat", "baslik": "İzlenebilirlik sistemi kur", "aciklama": "Hammaddeden sevkiyata izlenebilirlik sağlayın."},
    {"id": "adim3", "asama": "Aşama 1: Eksikleri Kapat", "baslik": "FMEA çalışması yap", "aciklama": "Tasarım ve süreç FMEA'larını oluşturun."},
    {"id": "adim4", "asama": "Aşama 1: Eksikleri Kapat", "baslik": "Üretim süreç prosedürlerini yaz", "aciklama": "Tüm kritik süreçleri yazılı hale getirin."},
    {"id": "adim5", "asama": "Aşama 1: Eksikleri Kapat", "baslik": "Doküman kontrol prosedürü oluştur", "aciklama": "Doküman kontrolünü sistematik hale getirin."},
    {"id": "adim6", "asama": "Aşama 2: İç Denetim", "baslik": "İç denetim planı hazırla", "aciklama": "Yıllık iç denetim planı oluşturun."},
    {"id": "adim7", "asama": "Aşama 2: İç Denetim", "baslik": "İç denetimi gerçekleştir", "aciklama": "Planlanan denetimi yapın ve raporlayın."},
    {"id": "adim8", "asama": "Aşama 2: İç Denetim", "baslik": "Düzeltici faaliyetleri kapat", "aciklama": "Bulunan uygunsuzlukları kapatın."},
    {"id": "adim9", "asama": "Aşama 2: İç Denetim", "baslik": "Yönetim gözden geçirme toplantısı yap", "aciklama": "Üst yönetimle gözden geçirme yapın."},
    {"id": "adim10", "asama": "Aşama 3: Belgelendirme Denetimi", "baslik": "Belgelendirme kuruluşu seç", "aciklama": "Akredite bir kuruluş seçin."},
    {"id": "adim11", "asama": "Aşama 3: Belgelendirme Denetimi", "baslik": "Aşama 1 denetimi", "aciklama": "Doküman incelemesini tamamlayın."},
    {"id": "adim12", "asama": "Aşama 3: Belgelendirme Denetimi", "baslik": "Aşama 2 denetimi", "aciklama": "Saha denetimini tamamlayın."},
    {"id": "adim13", "asama": "Aşama 3: Belgelendirme Denetimi", "baslik": "Sertifikayı al", "aciklama": "AS9100 sertifikanızı alın."},
]

@app.get("/yol-haritasi/{email}")
def yol_haritasi_getir(email: str, db: Session = Depends(get_db)):
    tamamlananlar = db.query(YolHaritasi).filter(
        YolHaritasi.kullanici_email == email,
        YolHaritasi.tamamlandi == 1
    ).all()
    tamamlanan_idler = [t.adim_id for t in tamamlananlar]
    
    adimlar = [{**a, "tamamlandi": a["id"] in tamamlanan_idler} for a in YOL_HARITASI_ADIMLARI]
    
    asamalar = {}
    for a in adimlar:
        if a["asama"] not in asamalar:
            asamalar[a["asama"]] = []
        asamalar[a["asama"]].append(a)
    
    toplam = len(YOL_HARITASI_ADIMLARI)
    tamamlanan = len(tamamlanan_idler)
    yuzde = round((tamamlanan / toplam) * 100) if toplam > 0 else 0
    
    return {
        "email": email, "toplam_adim": toplam,
        "tamamlanan_adim": tamamlanan, "ilerleme_yuzdesi": yuzde,
        "asamalar": asamalar
    }

@app.post("/yol-haritasi/tamamla")
def yol_haritasi_tamamla(email: str, adim_id: str, db: Session = Depends(get_db)):
    mevcut = db.query(YolHaritasi).filter(
        YolHaritasi.kullanici_email == email, YolHaritasi.adim_id == adim_id
    ).first()
    
    if mevcut:
        mevcut.tamamlandi = 1
        mevcut.tamamlanma_tarihi = datetime.utcnow()
    else:
        db.add(YolHaritasi(kullanici_email=email, adim_id=adim_id, tamamlandi=1))
    db.commit()
    return {"mesaj": "Adım tamamlandı"}

@app.post("/yol-haritasi/geri-al")
def yol_haritasi_geri_al(email: str, adim_id: str, db: Session = Depends(get_db)):
    mevcut = db.query(YolHaritasi).filter(
        YolHaritasi.kullanici_email == email, YolHaritasi.adim_id == adim_id
    ).first()
    if mevcut:
        mevcut.tamamlandi = 0
        db.commit()
    return {"mesaj": "Adım geri alındı"}


# ==================== DENETİM SİMÜLASYONU ====================

@app.post("/denetim-mesaj")
def denetim_mesaj(girdi: DenetimMesajGirdi):
    try:
        asistan_sayisi = len([m for m in girdi.mesajlar if m.get("role") == "assistant"])
        
        konusma_metni = ""
        for m in girdi.mesajlar:
            if m.get("role") == "assistant":
                konusma_metni += "\n🤖 DENETÇİ: " + m.get("content", "") + "\n"
            elif m.get("role") == "user":
                konusma_metni += "\n👤 KOBİ: " + m.get("content", "") + "\n"
        
        if asistan_sayisi >= 4:
            ozet_prompt = (
                "AS9100 Rev D denetim simülasyonu dökümü:\n" + konusma_metni +
                "\n\nGÖREV: Bu konuşmayı değerlendir. SADECE aşağıdaki formatta özet ver. "
                "Soru SORMA, selamlama YAPMA.\n\n"
                "📊 DENETİM ÖZETİ\n\n"
                "**Genel Değerlendirme:**\n(2-3 cümle)\n\n"
                "**✅ Güçlü Yönler:**\n- (En az 3 madde)\n\n"
                "**⚠️ Zayıf Yönler:**\n- (En az 3 madde)\n\n"
                "**💡 Öneriler:**\n- (En az 3 madde)\n\n"
                "**📈 Tahmini AS9100 Uygunluk Skoru:**\n(X/100)"
            )
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": ozet_prompt}],
                temperature=0.3
            )
            
            return {
                "basarili": True,
                "mesaj": response.choices[0].message.content,
                "soru_sayisi": asistan_sayisi,
                "ozet_mi": True
            }
        
        sistem_prompt = (
            'Sen AS9100 Rev D sertifikasyon denetçisisin. '
            '"' + (girdi.sirket_adi or "KOBİ") + '" firmasının kalite yöneticisiyle '
            "denetim simülasyonu yapıyorsun.\n\n"
            "KURALLAR:\n"
            "1. Her mesajda: KOBİ'nin son cevabını değerlendir + YENİ 1 soru sor.\n"
            "2. En fazla 3-4 cümle + 1 soru.\n"
            "3. Türkçe cevap ver.\n"
            "4. Konular: Risk (6.1), Doküman (7.5), İç Denetim (9.2), "
            "Düzeltici Faaliyet (10.2), İzlenebilirlik (8.5.2), Kalibrasyon (7.1.5), "
            "Eğitim (7.2), Üretim (8.5), Tasarım (8.3), Satın Alma (8.4)."
        )
        
        mesajlar = [{"role": "system", "content": sistem_prompt}]
        mesajlar.extend(girdi.mesajlar)
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=mesajlar,
            temperature=0.7
        )
        
        return {
            "basarili": True,
            "mesaj": response.choices[0].message.content,
            "soru_sayisi": asistan_sayisi + 1,
            "ozet_mi": False
        }
    except Exception as e:
        return {"basarili": False, "hata": "Denetim mesajı alınamadı: " + str(e)}


# ==================== ŞABLON WORD ====================

@app.post("/sablon-word-indir")
def sablon_word_indir(girdi: SablonWordGirdi):
    try:
        html = girdi.icerik_html
        html = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n[H1]\1[/H1]\n', html, flags=re.DOTALL)
        html = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n[H2]\1[/H2]\n', html, flags=re.DOTALL)
        html = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n[H3]\1[/H3]\n', html, flags=re.DOTALL)
        html = re.sub(r'<p[^>]*>(.*?)</p>', r'\n[P]\1[/P]\n', html, flags=re.DOTALL)
        html = re.sub(r'<li[^>]*>(.*?)</li>', r'\n[LI]\1[/LI]\n', html, flags=re.DOTALL)
        html = re.sub(r'<td[^>]*>(.*?)</td>', r'|\1', html, flags=re.DOTALL)
        html = re.sub(r'<th[^>]*>(.*?)</th>', r'|\1', html, flags=re.DOTALL)
        html = re.sub(r'<tr[^>]*>(.*?)</tr>', r'\n[TR]\1[/TR]\n', html, flags=re.DOTALL)
        html = re.sub(r'<[^>]+>', '', html)
        html = html.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        
        rtf = r"{\rtf1\ansi\ansicpg1254\deff0" + "\n"
        rtf += r"{\fonttbl{\f0\fnil\fcharset162 Calibri;}}" + "\n"
        rtf += r"{\colortbl;\red0\green0\blue0;\red0\green119\blue182;\red10\green25\blue41;}" + "\n"
        rtf += r"\viewkind4\uc1\pard\f0\fs22" + "\n"
        
        def escape_rtf(text):
            text = text.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')
            text = text.replace('ş', "\\'fe").replace('Ş', "\\'de")
            text = text.replace('ğ', "\\'f0").replace('Ğ', "\\'d0")
            text = text.replace('ı', "\\'fd").replace('İ', "\\'dd")
            text = text.replace('ö', "\\'f6").replace('Ö', "\\'d6")
            text = text.replace('ü', "\\'fc").replace('Ü', "\\'dc")
            text = text.replace('ç', "\\'e7").replace('Ç', "\\'c7")
            return text
        
        for satir in html.split('\n'):
            satir = satir.strip()
            if not satir:
                continue
            if satir.startswith('[H1]') and satir.endswith('[/H1]'):
                rtf += r"\pard\qc\cf3\b\fs36 " + escape_rtf(satir[4:-5].strip()) + r"\b0\fs22\par\n"
            elif satir.startswith('[H2]') and satir.endswith('[/H2]'):
                rtf += r"\pard\cf2\b\fs28 " + escape_rtf(satir[4:-5].strip()) + r"\b0\fs22\par\n"
            elif satir.startswith('[H3]') and satir.endswith('[/H3]'):
                rtf += r"\pard\cf3\b\fs24 " + escape_rtf(satir[4:-5].strip()) + r"\b0\fs22\par\n"
            elif satir.startswith('[P]') and satir.endswith('[/P]'):
                rtf += r"\pard\cf1 " + escape_rtf(satir[3:-4].strip()) + r"\par\n"
            elif satir.startswith('[LI]') and satir.endswith('[/LI]'):
                rtf += r"\pard\li720\cf1 \bullet " + escape_rtf(satir[4:-5].strip()) + r"\par\n"
            elif satir.startswith('[TR]') and satir.endswith('[/TR]'):
                rtf += r"\pard\cf1 " + escape_rtf(satir[4:-5].strip()) + r"\par\n"
            else:
                rtf += r"\pard\cf1 " + escape_rtf(satir) + r"\par\n"
        
        rtf += "}"
        
        buffer = io.BytesIO()
        buffer.write(rtf.encode('utf-8'))
        buffer.seek(0)
        
        dosya_adi = girdi.baslik.replace(' ', '_').replace('/', '_') + '.rtf'
        
        return StreamingResponse(
            buffer, media_type="application/rtf",
            headers={"Content-Disposition": f"attachment; filename={dosya_adi}"}
        )
    except Exception as e:
        return {"basarili": False, "hata": f"Word oluşturulamadı: {str(e)}"}


# ==================== HATIRLATICI ====================

@app.post("/hatirlatici-ekle")
def hatirlatici_ekle(girdi: HatirlaticiGirdi, db: Session = Depends(get_db)):
    yeni = Hatirlatici(
        kullanici_email=girdi.kullanici_email,
        baslik=girdi.baslik, aciklama=girdi.aciklama,
        tarih=girdi.tarih, tip=girdi.tip
    )
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    return {"mesaj": "Hatırlatıcı eklendi", "id": yeni.id}

@app.get("/hatirlaticilar")
def hatirlatici_listele(email: str, db: Session = Depends(get_db)):
    kayitlar = db.query(Hatirlatici).filter(
        Hatirlatici.kullanici_email == email, Hatirlatici.aktif == 1
    ).order_by(Hatirlatici.tarih).all()
    return {
        "toplam": len(kayitlar),
        "hatirlaticilar": [{
            "id": h.id, "baslik": h.baslik, "aciklama": h.aciklama,
            "tarih": h.tarih, "tip": h.tip
        } for h in kayitlar]
    }

@app.delete("/hatirlatici-sil/{hatirlatici_id}")
def hatirlatici_sil(hatirlatici_id: int, db: Session = Depends(get_db)):
    kayit = db.query(Hatirlatici).filter(Hatirlatici.id == hatirlatici_id).first()
    if not kayit:
        raise HTTPException(status_code=404, detail="Bulunamadı")
    kayit.aktif = 0
    db.commit()
    return {"mesaj": "Silindi"}

@app.post("/hatirlatici-test-gonder/{hatirlatici_id}")
def hatirlatici_test_gonder(hatirlatici_id: int, db: Session = Depends(get_db)):
    kayit = db.query(Hatirlatici).filter(Hatirlatici.id == hatirlatici_id).first()
    if not kayit:
        raise HTTPException(status_code=404, detail="Bulunamadı")
    
    email_gonder(
        konu=f"🔔 HATIRLATICI: {kayit.baslik}",
        icerik=f"📌 {kayit.baslik}\n📅 {kayit.tarih}\n📝 {kayit.aciklama}\n🏷️ {kayit.tip}"
    )
    return {"mesaj": "Test gönderildi"}


# ==================== KALİBRASYON ====================

@app.post("/kalibrasyon-ekle")
def kalibrasyon_ekle(girdi: KalibrasyonGirdi, db: Session = Depends(get_db)):
    yeni = Kalibrasyon(
        kullanici_email=girdi.kullanici_email,
        ekipman_adi=girdi.ekipman_adi,
        marka_model=girdi.marka_model,
        seri_no=girdi.seri_no,
        konum=girdi.konum,
        son_kalibrasyon=girdi.son_kalibrasyon,
        sonraki_kalibrasyon=girdi.sonraki_kalibrasyon,
        kalibrasyon_firmasi=girdi.kalibrasyon_firmasi,
        sertifika_no=girdi.sertifika_no,
        notlar=girdi.notlar
    )
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    
    # Hatırlatıcı oluştur (30 gün önce)
    try:
        sonraki = datetime.strptime(girdi.sonraki_kalibrasyon, "%Y-%m-%d")
        hatirlatma = sonraki - timedelta(days=30)
        db.add(Hatirlatici(
            kullanici_email=girdi.kullanici_email,
            baslik=f"Kalibrasyon: {girdi.ekipman_adi}",
            aciklama=f"Sertifika: {girdi.sertifika_no or '—'}",
            tarih=hatirlatma.strftime("%Y-%m-%d"),
            tip="kalibrasyon"
        ))
        db.commit()
    except Exception as e:
        print(f"Hatırlatıcı oluşturulamadı: {e}")
    
    return {"mesaj": "Kalibrasyon eklendi", "id": yeni.id}

@app.get("/kalibrasyonlar")
def kalibrasyon_listele(email: str, db: Session = Depends(get_db)):
    kayitlar = db.query(Kalibrasyon).filter(
        Kalibrasyon.kullanici_email == email,
        Kalibrasyon.durum == "aktif"
    ).order_by(Kalibrasyon.sonraki_kalibrasyon).all()
    
    bugun = datetime.utcnow().date()
    liste = []
    for k in kayitlar:
        try:
            sonraki = datetime.strptime(k.sonraki_kalibrasyon, "%Y-%m-%d").date()
            gun_fark = (sonraki - bugun).days
        except:
            gun_fark = 0
        
        if gun_fark < 0:
            durum, renk = "gecmis", "kirmizi"
        elif gun_fark <= 30:
            durum, renk = "yaklasiyor", "sari"
        else:
            durum, renk = "gecerli", "yesil"
        
        liste.append({
            "id": k.id, "ekipman_adi": k.ekipman_adi,
            "marka_model": k.marka_model, "seri_no": k.seri_no,
            "konum": k.konum, "son_kalibrasyon": k.son_kalibrasyon,
            "sonraki_kalibrasyon": k.sonraki_kalibrasyon,
            "kalibrasyon_firmasi": k.kalibrasyon_firmasi,
            "sertifika_no": k.sertifika_no, "notlar": k.notlar,
            "gun_fark": gun_fark, "durum": durum, "renk": renk
        })
    
    return {"toplam": len(liste), "kalibrasyonlar": liste}

@app.put("/kalibrasyon-guncelle/{kalibrasyon_id}")
def kalibrasyon_guncelle(
    kalibrasyon_id: int, son_kalibrasyon: str, sonraki_kalibrasyon: str,
    sertifika_no: str = "", db: Session = Depends(get_db)
):
    kayit = db.query(Kalibrasyon).filter(Kalibrasyon.id == kalibrasyon_id).first()
    if not kayit:
        raise HTTPException(status_code=404, detail="Bulunamadı")
    kayit.son_kalibrasyon = son_kalibrasyon
    kayit.sonraki_kalibrasyon = sonraki_kalibrasyon
    if sertifika_no:
        kayit.sertifika_no = sertifika_no
    db.commit()
    return {"mesaj": "Güncellendi"}

@app.delete("/kalibrasyon-sil/{kalibrasyon_id}")
def kalibrasyon_sil(kalibrasyon_id: int, db: Session = Depends(get_db)):
    kayit = db.query(Kalibrasyon).filter(Kalibrasyon.id == kalibrasyon_id).first()
    if not kayit:
        raise HTTPException(status_code=404, detail="Bulunamadı")
    kayit.durum = "pasif"
    db.commit()
    return {"mesaj": "Silindi"}


# ==================== STATİK ====================
# ==================== ÖDEME (iyzico Sandbox) ====================

PLAN_FIYATLARI = {
    "temel": "2000.0",
    "profesyonel": "5000.0"
}

@app.post("/odeme-baslat")
def odeme_baslat(email: str, plan: str = "profesyonel"):
    try:
        if plan not in PLAN_FIYATLARI:
            return {"basarili": False, "hata": "Geçersiz plan"}
        
        fiyat = PLAN_FIYATLARI[plan]
        
        # Kullanıcıyı bul
        db = SessionLocal()
        kullanici = db.query(Kullanici).filter(Kullanici.email == email).first()
        if not kullanici:
            db.close()
            return {"basarili": False, "hata": "Kullanıcı bulunamadı"}
        
        kullanici_id = kullanici.id
        sirket_adi = kullanici.sirket_adi or "Kullanici"
        db.close()
        
        # iyzico istek objesi (sözlük formatında)
        request = {
            'locale': 'tr',
            'conversationId': str(int(datetime.now().timestamp())),
            'price': fiyat,
            'paidPrice': fiyat,
            'currency': 'TRY',
            'basketId': 'B' + str(int(datetime.now().timestamp())),
            'paymentGroup': 'PRODUCT',
            'callbackUrl': '/odeme-callback',
            'enabledInstallments': [1, 2, 3, 6],
            'buyer': {
                'id': str(kullanici_id),
                'name': sirket_adi[:50],
                'surname': 'Yetkili',
                'gsmNumber': '+905000000000',
                'email': email,
                'identityNumber': '11111111111',
                'lastLoginDate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'registrationDate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'registrationAddress': 'Turkiye',
                'ip': '127.0.0.1',
                'city': 'Istanbul',
                'country': 'Turkey'
            },
            'shippingAddress': {
                'contactName': sirket_adi[:50],
                'city': 'Istanbul',
                'country': 'Turkey',
                'address': 'Turkiye'
            },
            'billingAddress': {
                'contactName': sirket_adi[:50],
                'city': 'Istanbul',
                'country': 'Turkey',
                'address': 'Turkiye'
            },
            'basketItems': [
                {
                    'id': 'BI' + str(int(datetime.now().timestamp())),
                    'name': plan.capitalize() + ' Plan',
                    'category1': 'SaaS',
                    'itemType': 'VIRTUAL',
                    'price': fiyat
                }
            ]
        }
        
             # iyzico'ya gönder
        response = iyzipay.CheckoutFormInitialize().create(request, iyzico_options)
        
        # Yanıtı oku ve JSON'a çevir
        response_data = json.loads(response.read().decode('utf-8'))
        
        if response_data.get('status') == 'success':
            return {
                "basarili": True,
                "token": response_data.get('token'),
                "payment_page_url": response_data.get('paymentPageUrl'),
                "plan": plan,
                "fiyat": fiyat
            }
        else:
            return {
                "basarili": False,
                "hata": response_data.get('errorMessage', 'Ödeme başlatılamadı')
            }
    
    except Exception as e:
        return {"basarili": False, "hata": f"Hata: {str(e)}"}


@app.post("/odeme-callback")
def odeme_callback(token: str = Form("")):
    try:
        request = {'token': token}
        response = iyzipay.CheckoutForm().retrieve(request, iyzico_options)
        response_data = json.loads(response.read().decode('utf-8'))
        
        if response_data.get('status') == 'success' and response_data.get('paymentStatus') == 'SUCCESS':
            # Başarılı ödeme - kullanıcının planını güncelle
            email = response_data.get('buyer', {}).get('email', '')
            basket_items = response_data.get('basketItems', [])
            
            if basket_items and email:
                plan_adi = basket_items[0].get('name', '').replace(' Plan', '').lower()
                
                # Planı veritabanında güncelle
                db = SessionLocal()
                kullanici = db.query(Kullanici).filter(Kullanici.email == email).first()
                if kullanici and plan_adi in ['temel', 'profesyonel', 'kurumsal']:
                    kullanici.plan = plan_adi
                    db.commit()
                db.close()
            
            email_gonder(
                konu="💰 Yeni Ödeme Alındı",
                icerik=f"E-posta: {email}\nTutar: {response_data.get('paidPrice')} TL\nDurum: Başarılı"
            )
            
            # Başarılı HTML sayfası döndür
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html lang="tr">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Ödeme Başarılı</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', sans-serif;
                        background: linear-gradient(135deg, #0a1929 0%, #1a3a5c 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        padding: 20px;
                    }}
                    .kart {{
                        background: rgba(255,255,255,0.05);
                        border-radius: 20px;
                        padding: 50px 40px;
                        text-align: center;
                        max-width: 500px;
                        border: 1px solid rgba(74, 222, 128, 0.3);
                    }}
                    .ikon {{
                        font-size: 80px;
                        margin-bottom: 20px;
                    }}
                    h1 {{
                        color: #4ade80;
                        margin-bottom: 15px;
                        font-size: 28px;
                    }}
                    p {{
                        color: #a8c5e0;
                        font-size: 16px;
                        line-height: 1.6;
                        margin-bottom: 30px;
                    }}
                    .btn {{
                        display: inline-block;
                        background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%);
                        color: white;
                        padding: 15px 35px;
                        border-radius: 50px;
                        text-decoration: none;
                        font-weight: 600;
                        font-size: 16px;
                        transition: all 0.3s;
                    }}
                    .btn:hover {{
                        transform: translateY(-3px);
                        box-shadow: 0 12px 30px rgba(0,180,216,0.4);
                    }}
                </style>
            </head>
            <body>
                <div class="kart">
                    <div class="ikon">✅</div>
                    <h1>Ödeme Başarılı!</h1>
                    <p>
                        Planınız aktif edildi.<br>
                        Fatura e-posta adresinize gönderilecek.<br>
                        Yeni özelliklerin tadını çıkarın!
                    </p>
                    <a href="/static/panel.html" class="btn">Panele Dön →</a>
                </div>
            </body>
            </html>
            """, status_code=200)
        else:
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html lang="tr">
            <head>
                <meta charset="UTF-8">
                <title>Ödeme Başarısız</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', sans-serif;
                        background: linear-gradient(135deg, #0a1929 0%, #1a3a5c 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        padding: 20px;
                    }}
                    .kart {{
                        background: rgba(255,255,255,0.05);
                        border-radius: 20px;
                        padding: 50px 40px;
                        text-align: center;
                        max-width: 500px;
                        border: 1px solid rgba(239, 68, 68, 0.3);
                    }}
                    .ikon {{ font-size: 80px; margin-bottom: 20px; }}
                    h1 {{ color: #ef4444; margin-bottom: 15px; font-size: 28px; }}
                    p {{ color: #a8c5e0; font-size: 16px; line-height: 1.6; margin-bottom: 30px; }}
                    .btn {{
                        display: inline-block;
                        background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%);
                        color: white;
                        padding: 15px 35px;
                        border-radius: 50px;
                        text-decoration: none;
                        font-weight: 600;
                    }}
                </style>
            </head>
            <body>
                <div class="kart">
                    <div class="ikon">❌</div>
                    <h1>Ödeme Başarısız</h1>
                    <p>Ödeme işlemi tamamlanamadı.<br>Lütfen tekrar deneyin veya destek ekibiyle iletişime geçin.</p>
                    <a href="/static/fiyatlandirma.html" class="btn">Tekrar Dene →</a>
                </div>
            </body>
            </html>
            """, status_code=200)
    
    except Exception as e:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <title>Hata</title>
        </head>
        <body style="background: #0a1929; color: white; font-family: sans-serif; padding: 50px; text-align: center;">
            <h1>❌ Bir hata oluştu</h1>
            <p>{str(e)}</p>
            <a href="/static/fiyatlandirma.html" style="color: #00b4d8;">← Geri Dön</a>
        </body>
        </html>
        """, status_code=200)
# ==================== UZMAN DANIŞMAN AĞI ====================

class UzmanKayitGirdi(BaseModel):
    ad_soyad: str
    email: str
    telefon: str = ""
    uzmanlik_alani: str
    deneyim_yili: int = 0
    sertifikalar: str = ""
    referanslar: str = ""
    fiyat_araligi: str = ""
    sehir: str = ""


class RandevuGirdi(BaseModel):
    kobi_email: str
    uzman_id: int
    hizmet_turu: str
    tarih: str
    saat: str


class YorumGirdi(BaseModel):
    randevu_id: int
    kobi_email: str
    uzman_id: int
    puan: int
    yorum: str = ""


@app.get("/uzmanlar")
def uzmanlari_listele(uzmanlik: str = None, sehir: str = None, db: Session = Depends(get_db)):
    sorgu = db.query(Uzman).filter(Uzman.onay_durumu == "onayli")
    if uzmanlik:
        sorgu = sorgu.filter(Uzman.uzmanlik_alani.contains(uzmanlik))
    if sehir:
        sorgu = sorgu.filter(Uzman.sehir == sehir)
    uzmanlar = sorgu.order_by(Uzman.puan.desc()).all()
    return {
        "toplam": len(uzmanlar),
        "uzmanlar": [{
            "id": u.id, "ad_soyad": u.ad_soyad, "email": u.email,
            "telefon": u.telefon, "uzmanlik_alani": u.uzmanlik_alani,
            "deneyim_yili": u.deneyim_yili, "sertifikalar": u.sertifikalar,
            "referanslar": u.referanslar, "fiyat_araligi": u.fiyat_araligi,
            "sehir": u.sehir, "puan": u.puan, "toplam_is": u.toplam_is,
            "profil_fotografi": u.profil_fotografi
        } for u in uzmanlar]
    }


@app.get("/uzman/{uzman_id}")
def uzman_detay(uzman_id: int, db: Session = Depends(get_db)):
    uzman = db.query(Uzman).filter(Uzman.id == uzman_id).first()
    if not uzman:
        raise HTTPException(status_code=404, detail="Uzman bulunamadı")
    
    yorumlar = db.query(UzmanYorum).filter(
        UzmanYorum.uzman_id == uzman_id
    ).order_by(UzmanYorum.olusturma_tarihi.desc()).all()
    
    return {
        "uzman": {
            "id": uzman.id, "ad_soyad": uzman.ad_soyad, "email": uzman.email,
            "telefon": uzman.telefon, "uzmanlik_alani": uzman.uzmanlik_alani,
            "deneyim_yili": uzman.deneyim_yili, "sertifikalar": uzman.sertifikalar,
            "referanslar": uzman.referanslar, "fiyat_araligi": uzman.fiyat_araligi,
            "sehir": uzman.sehir, "puan": uzman.puan, "toplam_is": uzman.toplam_is,
            "profil_fotografi": uzman.profil_fotografi, "onay_durumu": uzman.onay_durumu
        },
        "yorumlar": [{
            "id": y.id, "puan": y.puan, "yorum": y.yorum,
            "kobi_email": y.kobi_email,
            "tarih": y.olusturma_tarihi.isoformat()
        } for y in yorumlar]
    }


@app.post("/uzman/kayit")
def uzman_kayit(girdi: UzmanKayitGirdi, db: Session = Depends(get_db)):
    mevcut = db.query(Uzman).filter(Uzman.email == girdi.email).first()
    if mevcut:
        raise HTTPException(status_code=400, detail="Bu email zaten kayıtlı")
    
    yeni = Uzman(
        ad_soyad=girdi.ad_soyad, email=girdi.email, telefon=girdi.telefon,
        uzmanlik_alani=girdi.uzmanlik_alani, deneyim_yili=girdi.deneyim_yili,
        sertifikalar=girdi.sertifikalar, referanslar=girdi.referanslar,
        fiyat_araligi=girdi.fiyat_araligi, sehir=girdi.sehir,
        onay_durumu="beklemede"
    )
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    
    email_gonder(
        konu=f"Yeni Uzman Başvurusu: {girdi.ad_soyad}",
        icerik=f"Ad: {girdi.ad_soyad}\nEmail: {girdi.email}\nUzmanlık: {girdi.uzmanlik_alani}\nŞehir: {girdi.sehir}"
    )
    
    return {"mesaj": "Başvurunuz alındı. Onay sonrası yayına alınacak.", "id": yeni.id}


@app.post("/randevu")
def randevu_olustur(girdi: RandevuGirdi, db: Session = Depends(get_db)):
    uzman = db.query(Uzman).filter(Uzman.id == girdi.uzman_id).first()
    if not uzman:
        raise HTTPException(status_code=404, detail="Uzman bulunamadı")
    
    yeni = Randevu(
        kobi_email=girdi.kobi_email, uzman_id=girdi.uzman_id,
        hizmet_turu=girdi.hizmet_turu, tarih=girdi.tarih,
        saat=girdi.saat, durum="beklemede"
    )
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    
    email_gonder(
        konu=f"Yeni Randevu Talebi: {girdi.hizmet_turu}",
        icerik=f"Uzman: {uzman.ad_soyad}\nKOBİ: {girdi.kobi_email}\nTarih: {girdi.tarih} {girdi.saat}"
    )
    
    return {"mesaj": "Randevu talebiniz alındı", "id": yeni.id}


@app.get("/randevularim")
def randevularim(email: str, db: Session = Depends(get_db)):
    randevular = db.query(Randevu).filter(
        Randevu.kobi_email == email
    ).order_by(Randevu.olusturma_tarihi.desc()).all()
    
    liste = []
    for r in randevular:
        uzman = db.query(Uzman).filter(Uzman.id == r.uzman_id).first()
        liste.append({
            "id": r.id, "uzman_id": r.uzman_id,
            "uzman_adi": uzman.ad_soyad if uzman else "—",
            "hizmet_turu": r.hizmet_turu, "tarih": r.tarih,
            "saat": r.saat, "durum": r.durum,
            "olusturma_tarihi": r.olusturma_tarihi.isoformat()
        })
    
    return {"toplam": len(liste), "randevular": liste}


@app.get("/uzman-randevulari/{uzman_id}")
def uzman_randevulari(uzman_id: int, db: Session = Depends(get_db)):
    randevular = db.query(Randevu).filter(
        Randevu.uzman_id == uzman_id
    ).order_by(Randevu.olusturma_tarihi.desc()).all()
    
    return {
        "toplam": len(randevular),
        "randevular": [{
            "id": r.id, "kobi_email": r.kobi_email,
            "hizmet_turu": r.hizmet_turu, "tarih": r.tarih,
            "saat": r.saat, "durum": r.durum
        } for r in randevular]
    }


@app.put("/randevu-durum/{randevu_id}")
def randevu_durum_guncelle(randevu_id: int, yeni_durum: str, db: Session = Depends(get_db)):
    randevu = db.query(Randevu).filter(Randevu.id == randevu_id).first()
    if not randevu:
        raise HTTPException(status_code=404, detail="Randevu bulunamadı")
    randevu.durum = yeni_durum
    db.commit()
    return {"mesaj": "Durum güncellendi", "durum": yeni_durum}


@app.post("/uzman-yorum")
def uzman_yorum(girdi: YorumGirdi, db: Session = Depends(get_db)):
    randevu = db.query(Randevu).filter(Randevu.id == girdi.randevu_id).first()
    if not randevu:
        raise HTTPException(status_code=404, detail="Randevu bulunamadı")
    
    yeni = UzmanYorum(
        randevu_id=girdi.randevu_id, kobi_email=girdi.kobi_email,
        uzman_id=girdi.uzman_id, puan=girdi.puan, yorum=girdi.yorum
    )
    db.add(yeni)
    
    # Uzmanın ortalama puanını güncelle
    tum_yorumlar = db.query(UzmanYorum).filter(
        UzmanYorum.uzman_id == girdi.uzman_id
    ).all()
    toplam_puan = sum(y.puan for y in tum_yorumlar) + girdi.puan
    toplam_sayi = len(tum_yorumlar) + 1
    ortalama = round(toplam_puan / toplam_sayi, 2)
    
    uzman = db.query(Uzman).filter(Uzman.id == girdi.uzman_id).first()
    if uzman:
        uzman.puan = ortalama
    
    db.commit()
    return {"mesaj": "Yorum eklendi", "ortalama_puan": ortalama}


@app.get("/admin/uzmanlar")
def admin_uzmanlar(db: Session = Depends(get_db)):
    uzmanlar = db.query(Uzman).order_by(Uzman.olusturma_tarihi.desc()).all()
    return {
        "toplam": len(uzmanlar),
        "uzmanlar": [{
            "id": u.id, "ad_soyad": u.ad_soyad, "email": u.email,
            "uzmanlik_alani": u.uzmanlik_alani, "sehir": u.sehir,
            "onay_durumu": u.onay_durumu, "puan": u.puan,
            "toplam_is": u.toplam_is,
            "olusturma_tarihi": u.olusturma_tarihi.isoformat()
        } for u in uzmanlar]
    }


@app.post("/admin/uzman-onay/{uzman_id}")
def admin_uzman_onay(uzman_id: int, onay: str = "onayli", db: Session = Depends(get_db)):
    uzman = db.query(Uzman).filter(Uzman.id == uzman_id).first()
    if not uzman:
        raise HTTPException(status_code=404, detail="Uzman bulunamadı")
    uzman.onay_durumu = onay
    db.commit()
    
    if onay == "onayli":
        email_gonder(
            konu="Uzman Başvurunuz Onaylandı",
            icerik=f"Sayın {uzman.ad_soyad}, başvurunuz onaylandı. Artık platformda görünüyorsunuz."
        )
    
    return {"mesaj": f"Uzman durumu '{onay}' olarak güncellendi"}

# ==================== ANA YÜKLENİCİ MODÜLÜ ====================

class AnaYukleniciKayit(BaseModel):
    sirket_adi: str
    email: str
    sifre: str
    yetkili_adi: str = ""
    telefon: str = ""
    website: str = ""


def eydep_seviye_hesapla(yuzde: int) -> str:
    if yuzde >= 85:
        return "A"
    elif yuzde >= 70:
        return "B"
    elif yuzde >= 50:
        return "C"
    elif yuzde >= 30:
        return "D"
    else:
        return "yok"


@app.post("/ana-yuklenici/kayit")
def ana_yuklenici_kayit(girdi: AnaYukleniciKayit, db: Session = Depends(get_db)):
    mevcut = db.query(AnaYuklenici).filter(AnaYuklenici.email == girdi.email).first()
    if mevcut:
        raise HTTPException(status_code=400, detail="Bu email zaten kayıtlı")

    yeni = AnaYuklenici(
        sirket_adi=girdi.sirket_adi,
        email=girdi.email,
        sifre_hash=sifre_hashle(girdi.sifre),
        yetkili_adi=girdi.yetkili_adi,
        telefon=girdi.telefon,
        website=girdi.website,
        onay_durumu="beklemede"
    )
    db.add(yeni)
    db.commit()
    db.refresh(yeni)

    email_gonder(
        konu=f"Yeni Ana Yüklenici Başvurusu: {girdi.sirket_adi}",
        icerik=f"Şirket: {girdi.sirket_adi}\nEmail: {girdi.email}\nYetkili: {girdi.yetkili_adi}"
    )

    return {"mesaj": "Başvurunuz alındı. Onay sonrası giriş yapabilirsiniz.", "id": yeni.id}


@app.post("/ana-yuklenici/giris")
def ana_yuklenici_giris(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    ana = db.query(AnaYuklenici).filter(AnaYuklenici.email == form_data.username).first()
    if not ana or not sifre_dogrula(form_data.password, ana.sifre_hash):
        raise HTTPException(status_code=401, detail="Email veya şifre hatalı")
    if ana.onay_durumu != "onayli":
        raise HTTPException(status_code=403, detail="Hesabınız henüz onaylanmadı")

    token = token_olustur(data={"sub": ana.email, "rol": "ana_yuklenici"})

    return {
        "access_token": token,
        "token_type": "bearer",
        "ana_yuklenici": {
            "id": ana.id, "sirket_adi": ana.sirket_adi,
            "email": ana.email, "yetkili_adi": ana.yetkili_adi
        }
    }


@app.get("/ana-yuklenici/dashboard/{ana_id}")
def ana_yuklenici_dashboard(ana_id: int, db: Session = Depends(get_db)):
    ana = db.query(AnaYuklenici).filter(AnaYuklenici.id == ana_id).first()
    if not ana:
        raise HTTPException(status_code=404, detail="Ana yüklenici bulunamadı")

    tedarikciler = db.query(Kullanici).filter(Kullanici.ana_yuklenici_id == ana_id).all()

    toplam = len(tedarikciler)
    eydep_a = len([t for t in tedarikciler if t.eydep_seviye == "A"])
    eydep_b = len([t for t in tedarikciler if t.eydep_seviye == "B"])
    eydep_c = len([t for t in tedarikciler if t.eydep_seviye == "C"])
    eydep_d = len([t for t in tedarikciler if t.eydep_seviye == "D"])
    eydep_yok = len([t for t in tedarikciler if t.eydep_seviye == "yok"])

    return {
        "ana_yuklenici": {
            "id": ana.id, "sirket_adi": ana.sirket_adi,
            "email": ana.email, "yetkili_adi": ana.yetkili_adi
        },
        "ozet": {
            "toplam_tedarikci": toplam,
            "eydep_a": eydep_a, "eydep_b": eydep_b,
            "eydep_c": eydep_c, "eydep_d": eydep_d,
            "eydep_yok": eydep_yok
        },
        "tedarikciler": [{
            "id": t.id, "sirket_adi": t.sirket_adi,
            "email": t.email, "eydep_seviye": t.eydep_seviye,
            "eydep_skor": t.eydep_skor,
            "plan": t.plan, "rol": t.rol
        } for t in tedarikciler]
    }


@app.post("/ana-yuklenici/tedarikci-ekle")
def tedarikci_ekle(ana_id: int, tedarikci_email: str, db: Session = Depends(get_db)):
    ana = db.query(AnaYuklenici).filter(AnaYuklenici.id == ana_id).first()
    if not ana:
        raise HTTPException(status_code=404, detail="Ana yüklenici bulunamadı")

    tedarikci = db.query(Kullanici).filter(Kullanici.email == tedarikci_email).first()
    if not tedarikci:
        raise HTTPException(status_code=404, detail="Tedarikçi bulunamadı")

    tedarikci.ana_yuklenici_id = ana_id
    db.commit()

    return {"mesaj": f"{tedarikci.sirket_adi} tedarikçi ağınıza eklendi"}


@app.delete("/ana-yuklenici/tedarikci-cikar")
def tedarikci_cikar(ana_id: int, tedarikci_email: str, db: Session = Depends(get_db)):
    tedarikci = db.query(Kullanici).filter(
        Kullanici.email == tedarikci_email,
        Kullanici.ana_yuklenici_id == ana_id
    ).first()
    if not tedarikci:
        raise HTTPException(status_code=404, detail="Tedarikçi bulunamadı")
    tedarikci.ana_yuklenici_id = None
    db.commit()
    return {"mesaj": "Tedarikçi çıkarıldı"}


@app.get("/ana-yuklenici/eydep-dagilimi/{ana_id}")
def eydep_dagilimi(ana_id: int, db: Session = Depends(get_db)):
    """Ana yüklenicinin tedarikçi ağının EYDEP seviye dağılımı"""
    tedarikciler = db.query(Kullanici).filter(Kullanici.ana_yuklenici_id == ana_id).all()

    return {
        "toplam": len(tedarikciler),
        "seviyeler": {
            "A": [{"sirket_adi": t.sirket_adi, "email": t.email, "skor": t.eydep_skor}
                  for t in tedarikciler if t.eydep_seviye == "A"],
            "B": [{"sirket_adi": t.sirket_adi, "email": t.email, "skor": t.eydep_skor}
                  for t in tedarikciler if t.eydep_seviye == "B"],
            "C": [{"sirket_adi": t.sirket_adi, "email": t.email, "skor": t.eydep_skor}
                  for t in tedarikciler if t.eydep_seviye == "C"],
            "D": [{"sirket_adi": t.sirket_adi, "email": t.email, "skor": t.eydep_skor}
                  for t in tedarikciler if t.eydep_seviye == "D"],
            "yok": [{"sirket_adi": t.sirket_adi, "email": t.email, "skor": t.eydep_skor}
                    for t in tedarikciler if t.eydep_seviye == "yok"]
        }
    }


@app.get("/admin/ana-yukleniciler")
def admin_ana_yukleniciler(db: Session = Depends(get_db)):
    liste = db.query(AnaYuklenici).order_by(AnaYuklenici.olusturma_tarihi.desc()).all()
    return {
        "toplam": len(liste),
        "ana_yukleniciler": [{
            "id": a.id, "sirket_adi": a.sirket_adi, "email": a.email,
            "yetkili_adi": a.yetkili_adi, "telefon": a.telefon,
            "website": a.website, "onay_durumu": a.onay_durumu,
            "olusturma_tarihi": a.olusturma_tarihi.isoformat()
        } for a in liste]
    }


@app.post("/admin/ana-yuklenici-onay/{ana_id}")
def admin_ana_yuklenici_onay(ana_id: int, onay: str = "onayli", db: Session = Depends(get_db)):
    ana = db.query(AnaYuklenici).filter(AnaYuklenici.id == ana_id).first()
    if not ana:
        raise HTTPException(status_code=404, detail="Ana yüklenici bulunamadı")
    ana.onay_durumu = onay
    db.commit()

    if onay == "onayli":
        email_gonder(
            konu="Ana Yüklenici Başvurunuz Onaylandı",
            icerik=f"Sayın {ana.yetkili_adi or ana.sirket_adi}, hesabınız onaylandı. Panele giriş yapabilirsiniz."
        )

    return {"mesaj": f"Ana yüklenici durumu '{onay}' olarak güncellendi"}

# ==================== EĞİTİM MODÜLLERİ ====================

class EgitimKayitGirdi(BaseModel):
    baslik: str
    aciklama: str = ""
    kategori: str
    seviye: str = "baslangic"
    video_url: str = ""
    sure_dakika: int = 0
    fiyat: float = 0
    onizleme_metni: str = ""


class QuizGirdi(BaseModel):
    kullanici_email: str
    egitim_id: int
    cevaplar: Dict[str, str]  # {"1": "A", "2": "B", ...}


@app.get("/egitimler")
def egitimleri_listele(kategori: str = None, db: Session = Depends(get_db)):
    sorgu = db.query(Egitim).filter(Egitim.aktif == 1)
    if kategori:
        sorgu = sorgu.filter(Egitim.kategori == kategori)
    egitimler = sorgu.order_by(Egitim.olusturma_tarihi.desc()).all()
    return {
        "toplam": len(egitimler),
        "egitimler": [{
            "id": e.id, "baslik": e.baslik, "aciklama": e.aciklama,
            "kategori": e.kategori, "seviye": e.seviye,
            "sure_dakika": e.sure_dakika, "fiyat": e.fiyat,
            "video_url": e.video_url, "onizleme_metni": e.onizleme_metni
        } for e in egitimler]
    }


@app.get("/egitim/{egitim_id}")
def egitim_detay(egitim_id: int, db: Session = Depends(get_db)):
    egitim = db.query(Egitim).filter(Egitim.id == egitim_id).first()
    if not egitim:
        raise HTTPException(status_code=404, detail="Eğitim bulunamadı")

    sorular = db.query(EgitimSoru).filter(EgitimSoru.egitim_id == egitim_id).all()

    return {
        "egitim": {
            "id": egitim.id, "baslik": egitim.baslik,
            "aciklama": egitim.aciklama, "kategori": egitim.kategori,
            "seviye": egitim.seviye, "video_url": egitim.video_url,
            "sure_dakika": egitim.sure_dakika, "fiyat": egitim.fiyat,
            "onizleme_metni": egitim.onizleme_metni
        },
        "soru_sayisi": len(sorular)
    }


@app.get("/egitim/{egitim_id}/quiz")
def egitim_quiz(egitim_id: int, db: Session = Depends(get_db)):
    sorular = db.query(EgitimSoru).filter(EgitimSoru.egitim_id == egitim_id).all()
    return {
        "toplam": len(sorular),
        "sorular": [{
            "id": s.id, "soru": s.soru,
            "secenek_a": s.secenek_a, "secenek_b": s.secenek_b,
            "secenek_c": s.secenek_c, "secenek_d": s.secenek_d
        } for s in sorular]
    }


@app.post("/egitim/quiz-gonder")
def quiz_gonder(girdi: QuizGirdi, db: Session = Depends(get_db)):
    egitim = db.query(Egitim).filter(Egitim.id == girdi.egitim_id).first()
    if not egitim:
        raise HTTPException(status_code=404, detail="Eğitim bulunamadı")

    sorular = db.query(EgitimSoru).filter(EgitimSoru.egitim_id == girdi.egitim_id).all()

    if not sorular:
        raise HTTPException(status_code=400, detail="Bu eğitim için soru tanımlanmamış")

    dogru = 0
    toplam = len(sorular)
    detay = []

    for s in sorular:
        verilen = girdi.cevaplar.get(str(s.id), "").upper()
        dogru_mu = verilen == s.dogru_cevap.upper()
        if dogru_mu:
            dogru += 1
        detay.append({
            "soru_id": s.id, "soru": s.soru,
            "verilen": verilen, "dogru": s.dogru_cevap,
            "dogru_mu": dogru_mu
        })

    skor = round((dogru / toplam) * 100) if toplam > 0 else 0
    gecti = skor >= 70

    # İlerlemeyi kaydet
    mevcut = db.query(EgitimIlerleme).filter(
        EgitimIlerleme.kullanici_email == girdi.kullanici_email,
        EgitimIlerleme.egitim_id == girdi.egitim_id
    ).first()

    if mevcut:
        mevcut.quiz_skoru = max(mevcut.quiz_skoru, skor)
        mevcut.son_izleme_tarihi = datetime.utcnow()
        if gecti:
            mevcut.tamamlandi = 1
            mevcut.tamamlanma_tarihi = datetime.utcnow()
            mevcut.sertifika_alindi = 1
    else:
        yeni = EgitimIlerleme(
            kullanici_email=girdi.kullanici_email,
            egitim_id=girdi.egitim_id,
            tamamlandi=1 if gecti else 0,
            quiz_skoru=skor,
            sertifika_alindi=1 if gecti else 0,
            tamamlanma_tarihi=datetime.utcnow() if gecti else None
        )
        db.add(yeni)

    db.commit()

    return {
        "basarili": True,
        "skor": skor,
        "dogru": dogru,
        "toplam": toplam,
        "gecti": gecti,
        "detay": detay
    }


@app.get("/egitim/ilerleme/{email}")
def egitim_ilerleme(email: str, db: Session = Depends(get_db)):
    ilerlemeler = db.query(EgitimIlerleme).filter(
        EgitimIlerleme.kullanici_email == email
    ).all()

    liste = []
    for i in ilerlemeler:
        egitim = db.query(Egitim).filter(Egitim.id == i.egitim_id).first()
        liste.append({
            "egitim_id": i.egitim_id,
            "egitim_baslik": egitim.baslik if egitim else "—",
            "kategori": egitim.kategori if egitim else "—",
            "tamamlandi": i.tamamlandi,
            "quiz_skoru": i.quiz_skoru,
            "sertifika_alindi": i.sertifika_alindi,
            "tamamlanma_tarihi": i.tamamlanma_tarihi.isoformat() if i.tamamlanma_tarihi else None
        })

    return {"toplam": len(liste), "ilerlemeler": liste}


@app.post("/admin/egitim-ekle")
def admin_egitim_ekle(girdi: EgitimKayitGirdi, db: Session = Depends(get_db)):
    yeni = Egitim(
        baslik=girdi.baslik, aciklama=girdi.aciklama,
        kategori=girdi.kategori, seviye=girdi.seviye,
        video_url=girdi.video_url, sure_dakika=girdi.sure_dakika,
        fiyat=girdi.fiyat, onizleme_metni=girdi.onizleme_metni
    )
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    return {"mesaj": "Eğitim eklendi", "id": yeni.id}


@app.post("/admin/egitim-soru-ekle")
def admin_egitim_soru_ekle(
    egitim_id: int, soru: str,
    secenek_a: str, secenek_b: str, secenek_c: str, secenek_d: str,
    dogru_cevap: str, db: Session = Depends(get_db)
):
    yeni = EgitimSoru(
        egitim_id=egitim_id, soru=soru,
        secenek_a=secenek_a, secenek_b=secenek_b,
        secenek_c=secenek_c, secenek_d=secenek_d,
        dogru_cevap=dogru_cevap.upper()
    )
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    return {"mesaj": "Soru eklendi", "id": yeni.id}


@app.get("/admin/egitimler")
def admin_egitimler(db: Session = Depends(get_db)):
    egitimler = db.query(Egitim).order_by(Egitim.olusturma_tarihi.desc()).all()
    return {
        "toplam": len(egitimler),
        "egitimler": [{
            "id": e.id, "baslik": e.baslik, "kategori": e.kategori,
            "seviye": e.seviye, "sure_dakika": e.sure_dakika,
            "fiyat": e.fiyat, "aktif": e.aktif,
            "olusturma_tarihi": e.olusturma_tarihi.isoformat()
        } for e in egitimler]
    }
# Değerlendirme kaydedilirken EYDEP seviyesini de güncelle
# ==================== YETEN PORTAL ENTEGRASYONU ====================

class YETENBilgiGirdi(BaseModel):
    kullanici_email: str
    firma_adi: str = ""
    vergi_no: str = ""
    ticaret_sicil_no: str = ""
    yetkili_adi: str = ""
    telefon: str = ""
    email: str = ""
    website: str = ""
    sektor: str = ""
    calisan_sayisi: int = 0
    muhendis_sayisi: int = 0
    arge_personel_sayisi: int = 0
    ciro_son_yil: float = 0
    ciro_2_yil_once: float = 0
    ciro_3_yil_once: float = 0
    makine_parki: str = ""
    sertifikalar: str = ""
    urunler: str = ""
    arge_projeleri: str = ""
    patentler: str = ""


@app.post("/yeten-bilgi-kaydet")
def yeten_bilgi_kaydet(girdi: YETENBilgiGirdi, db: Session = Depends(get_db)):
    mevcut = db.query(YETENBilgi).filter(
        YETENBilgi.kullanici_email == girdi.kullanici_email
    ).first()

    if mevcut:
        # Güncelle
        for key, value in girdi.dict().items():
            if key != "kullanici_email":
                setattr(mevcut, key, value)
        mevcut.son_guncelleme = datetime.utcnow()
        # 3 ay sonrası hatırlatma
        hatirlatma = datetime.utcnow() + timedelta(days=90)
        mevcut.hatirlatma_tarihi = hatirlatma.strftime("%Y-%m-%d")
        db.commit()
        return {"mesaj": "YETEN bilgileri güncellendi", "id": mevcut.id}
    else:
        yeni = YETENBilgi(**girdi.dict())
        hatirlatma = datetime.utcnow() + timedelta(days=90)
        yeni.hatirlatma_tarihi = hatirlatma.strftime("%Y-%m-%d")
        db.add(yeni)
        db.commit()
        db.refresh(yeni)
        return {"mesaj": "YETEN bilgileri kaydedildi", "id": yeni.id}


@app.get("/yeten-bilgi/{email}")
def yeten_bilgi_getir(email: str, db: Session = Depends(get_db)):
    bilgi = db.query(YETENBilgi).filter(
        YETENBilgi.kullanici_email == email
    ).first()

    if not bilgi:
        return {"var": False, "bilgi": None}

    return {
        "var": True,
        "bilgi": {
            "id": bilgi.id, "firma_adi": bilgi.firma_adi,
            "vergi_no": bilgi.vergi_no, "ticaret_sicil_no": bilgi.ticaret_sicil_no,
            "yetkili_adi": bilgi.yetkili_adi, "telefon": bilgi.telefon,
            "email": bilgi.email, "website": bilgi.website,
            "sektor": bilgi.sektor, "calisan_sayisi": bilgi.calisan_sayisi,
            "muhendis_sayisi": bilgi.muhendis_sayisi,
            "arge_personel_sayisi": bilgi.arge_personel_sayisi,
            "ciro_son_yil": bilgi.ciro_son_yil,
            "ciro_2_yil_once": bilgi.ciro_2_yil_once,
            "ciro_3_yil_once": bilgi.ciro_3_yil_once,
            "makine_parki": bilgi.makine_parki,
            "sertifikalar": bilgi.sertifikalar,
            "urunler": bilgi.urunler,
            "arge_projeleri": bilgi.arge_projeleri,
            "patentler": bilgi.patentler,
            "yeten_kayit_durumu": bilgi.yeten_kayit_durumu,
            "eydep_seviye": bilgi.eydep_seviye,
            "son_guncelleme": bilgi.son_guncelleme.isoformat(),
            "hatirlatma_tarihi": bilgi.hatirlatma_tarihi
        }
    }


@app.get("/yeten-kontrol-listesi/{email}")
def yeten_kontrol_listesi(email: str, db: Session = Depends(get_db)):
    bilgi = db.query(YETENBilgi).filter(
        YETENBilgi.kullanici_email == email
    ).first()

    if not bilgi:
        return {"var": False, "eksikler": [], "tamamlanma": 0}

    # İdari, mali, teknik kriterler
    kriterler = {
        "idari": [
            ("firma_adi", "Firma Adı"),
            ("vergi_no", "Vergi Numarası"),
            ("ticaret_sicil_no", "Ticaret Sicil Numarası"),
            ("yetkili_adi", "Yetkili Adı Soyadı"),
            ("telefon", "Telefon"),
            ("email", "E-posta"),
            ("sektor", "Faaliyet Alanı/Sektör"),
            ("calisan_sayisi", "Çalışan Sayısı"),
        ],
        "mali": [
            ("ciro_son_yil", "Son Yıl Cirosu"),
            ("ciro_2_yil_once", "2 Yıl Önceki Ciro"),
            ("ciro_3_yil_once", "3 Yıl Önceki Ciro"),
        ],
        "teknik": [
            ("muhendis_sayisi", "Mühendis Sayısı"),
            ("arge_personel_sayisi", "Ar-Ge Personel Sayısı"),
            ("makine_parki", "Makine Parkı"),
            ("sertifikalar", "Sertifikalar"),
            ("urunler", "Ürünler"),
        ]
    }

    eksikler = {"idari": [], "mali": [], "teknik": []}
    toplam = 0
    dolu = 0

    for kategori, alanlar in kriterler.items():
        for alan_key, alan_adi in alanlar:
            toplam += 1
            deger = getattr(bilgi, alan_key, None)
            if deger is None or deger == "" or deger == 0:
                eksikler[kategori].append(alan_adi)
            else:
                dolu += 1

    tamamlanma = round((dolu / toplam) * 100) if toplam > 0 else 0

    return {
        "var": True,
        "tamamlanma": tamamlanma,
        "eksikler": eksikler,
        "toplam_eksik": sum(len(v) for v in eksikler.values())
    }


@app.post("/yeten-kayit-durumu-guncelle")
def yeten_kayit_durumu_guncelle(email: str, durum: str, db: Session = Depends(get_db)):
    bilgi = db.query(YETENBilgi).filter(YETENBilgi.kullanici_email == email).first()
    if not bilgi:
        raise HTTPException(status_code=404, detail="YETEN bilgisi bulunamadı")
    bilgi.yeten_kayit_durumu = durum
    db.commit()
    return {"mesaj": "Durum güncellendi", "durum": durum}


@app.get("/yeten-kopyala-format/{email}")
def yeten_kopyala_format(email: str, db: Session = Depends(get_db)):
    """YETEN portalına kopyala-yapıştır için hazır metin formatı"""
    bilgi = db.query(YETENBilgi).filter(YETENBilgi.kullanici_email == email).first()
    if not bilgi:
        raise HTTPException(status_code=404, detail="YETEN bilgisi bulunamadı")

    metin = f"""=== YETEN PORTAL KAYIT FORMATI ===

FİRMA BİLGİLERİ
Firma Adı: {bilgi.firma_adi}
Vergi No: {bilgi.vergi_no}
Ticaret Sicil No: {bilgi.ticaret_sicil_no}
Sektör: {bilgi.sektor}

YETKİLİ BİLGİLERİ
Yetkili Adı: {bilgi.yetkili_adi}
Telefon: {bilgi.telefon}
E-posta: {bilgi.email}
Web Sitesi: {bilgi.website}

İDARİ BİLGİLER
Çalışan Sayısı: {bilgi.calisan_sayisi}
Mühendis Sayısı: {bilgi.muhendis_sayisi}
Ar-Ge Personel Sayısı: {bilgi.arge_personel_sayisi}

MALİ BİLGİLER
Son Yıl Cirosu: {bilgi.ciro_son_yil} TL
2 Yıl Önceki Ciro: {bilgi.ciro_2_yil_once} TL
3 Yıl Önceki Ciro: {bilgi.ciro_3_yil_once} TL

TEKNİK BİLGİLER
Makine Parkı: {bilgi.makine_parki}
Sertifikalar: {bilgi.sertifikalar}
Ürünler: {bilgi.urunler}
Ar-Ge Projeleri: {bilgi.arge_projeleri}
Patentler: {bilgi.patentler}

=== BU METNİ YETEN PORTALINA KOPYALAYIN ===
"""

    return {"metin": metin}
# ==================== STATİK ====================
app.mount("/static", StaticFiles(directory=".", html=True), name="static")