"""
UyumOS — RegTech Modülleri Seed Script
AI Act için 20 soru ekler.
Çalıştırma: python seed_regtech.py
"""

from database import SessionLocal, RegTechSoru

def soru_var_mi(db, sektor, soru_no):
    return db.query(RegTechSoru).filter(
        RegTechSoru.sektor == sektor,
        RegTechSoru.soru_no == soru_no
    ).first() is not None

def soru_ekle(db, sektor, soru_no, soru, kategori, agirlik, aciklama=""):
    if soru_var_mi(db, sektor, soru_no):
        print(f"⏩ Zaten var: {sektor} - Soru {soru_no}")
        return
    yeni = RegTechSoru(
        sektor=sektor, soru_no=soru_no, soru=soru,
        kategori=kategori, agirlik=agirlik, aciklama=aciklama
    )
    db.add(yeni)
    print(f"✅ Soru {soru_no} eklendi ({kategori}, ağırlık: {agirlik})")

def main():
    db = SessionLocal()
    try:
        print("\n🚀 UyumOS RegTech Seed Başlıyor...\n")
        print("📋 AI Act Uyumluluk — 20 Soru\n")

        ai_act_sorular = [
            # === İDARİ (5 soru) ===
            (1, "Şirketinizin AI sistemleri envanteri var mı? Tüm AI sistemleri listelenmiş mi?", "idari", 3,
             "AI Act uyumluluğunun ilk adımı, kullanılan tüm AI sistemlerinin envanterini çıkarmaktır."),
            (2, "AI sistemlerinizin risk sınıflandırması yapıldı mı? (Yüksek/Sınırlı/Minimal risk)", "idari", 3,
             "AI Act'e göre her AI sistemi risk seviyesine göre sınıflandırılmalıdır. Yüksek riskli sistemler için ek yükümlülükler vardır."),
            (3, "AI Act uyumluluk sorumlusu atandı mı?", "idari", 2,
             "Uyumluluk sürecini yönetecek bir sorumlu atanması zorunludur."),
            (4, "AI sistemleri için yazılı politika ve prosedürler var mı?", "idari", 2,
             "AI kullanımı, geliştirme, risk yönetimi için yazılı politikalar olmalıdır."),
            (5, "Çalışanlara AI Act farkındalık eğitimi verildi mi?", "idari", 2,
             "AI sistemlerini kullanan/geliştiren tüm personele düzenli eğitim verilmelidir."),

            # === TEKNİK (6 soru) ===
            (6, "AI sistemlerinin teknik dokümantasyonu hazır mı?", "teknik", 3,
             "Her AI sistemi için teknik dokümantasyon (mimari, veri seti, model, test sonuçları) hazırlanmalıdır."),
            (7, "AI sistemlerinin veri yönetimi politikası var mı?", "teknik", 3,
             "Eğitim verisi, doğrulama verisi, kişisel veri yönetimi için politikalar olmalıdır."),
            (8, "AI modellerinin doğruluk ve performans testleri yapılıyor mu?", "teknik", 2,
             "Modellerin doğruluk, kesinlik, hatırlama gibi metriklerle test edilmesi gerekir."),
            (9, "AI sistemlerinde önyargı (bias) testi yapılıyor mu?", "teknik", 3,
             "AI modellerinin cinsiyet, ırk, yaş gibi konularda önyargılı olup olmadığı test edilmelidir."),
            (10, "AI sistemlerinin açıklanabilirlik (explainability) seviyesi belirlendi mi?", "teknik", 2,
             "AI kararlarının nasıl alındığı açıklanabilmelidir. Özellikle yüksek riskli sistemlerde."),
            (11, "AI sistemlerinin siber güvenlik önlemleri alındı mı?", "teknik", 2,
             "AI sistemleri siber saldırılara karşı korunmalıdır (model zehirleme, adversarial saldırılar)."),

            # === OPERASYONEL (9 soru) ===
            (12, "AI sistemleri için risk yönetim sistemi kuruldu mu?", "operasyonel", 3,
             "AI Act'e göre yüksek riskli sistemler için sürekli risk yönetim sistemi zorunludur."),
            (13, "AI sistemlerinin izlenmesi (monitoring) için süreç var mı?", "operasyonel", 2,
             "AI sistemlerinin performansı düzenli izlenmeli, sapmalar tespit edilmelidir."),
            (14, "AI olay müdahale planı var mı?", "operasyonel", 2,
             "AI sistemi arızası, yanlış karar, veri sızıntısı gibi durumlar için müdahale planı olmalıdır."),
            (15, "AI sistemleri için insan gözetimi (human oversight) sağlanıyor mu?", "operasyonel", 3,
             "Yüksek riskli AI sistemlerinde insan gözetimi zorunludur. Tam otomatik karar verilmemelidir."),
            (16, "AI tedarikçileriyle sözleşmelerde uyumluluk maddeleri var mı?", "operasyonel", 2,
             "Üçüncü taraf AI tedarikçileriyle yapılan sözleşmelerde AI Act uyumluluk maddeleri olmalıdır."),
            (17, "AI sistemlerinin kullanıcı bilgilendirmesi yapılıyor mu?", "operasyonel", 1,
             "Kullanıcılar, AI sistemiyle etkileşimde olduklarını bilmelidir (şeffaflık)."),
            (18, "AI sistemlerinin kayıt tutma (logging) mekanizması var mı?", "operasyonel", 2,
             "AI kararları, kullanıcı etkileşimleri, hatalar kayıt altına alınmalıdır."),
            (19, "AI Act kapsamında bildirim yükümlülükleri takip ediliyor mu?", "operasyonel", 2,
             "Ciddi olaylar, uygunsuzluklar yetkili otoritelere bildirilmelidir."),
            (20, "Düzenli AI Act uyumluluk denetimi yapılıyor mu?", "operasyonel", 2,
             "İç denetim ile AI Act uyumluluğu düzenli olarak kontrol edilmelidir."),
        ]

        for s in ai_act_sorular:
            soru_ekle(db, "ai_act", s[0], s[1], s[2], s[3], s[4])

        db.commit()
        print(f"\n✅ AI Act: {len(ai_act_sorular)} soru eklendi")

        print("\n🎉 RegTech Seed tamamlandı!")
        print(f"📊 Toplam: 1 sektör, {len(ai_act_sorular)} soru\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Hata: {e}\n")
    finally:
        db.close()

if __name__ == "__main__":
    main()