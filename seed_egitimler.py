"""
UyumOS — Eğitim Modülleri Seed Script
Bu script, 3 eğitim (FAI, FOD, YETEN) ve 30 quiz sorusu ekler.
Çalıştırma: python seed_egitimler.py
"""

from database import SessionLocal, Egitim, EgitimSoru

def egitim_var_mi(db, baslik):
    return db.query(Egitim).filter(Egitim.baslik == baslik).first() is not None

def egitim_ekle(db, baslik, aciklama, kategori, seviye, sure, fiyat, onizleme):
    if egitim_var_mi(db, baslik):
        print(f"⏩ Zaten var: {baslik}")
        return db.query(Egitim).filter(Egitim.baslik == baslik).first().id

    yeni = Egitim(
        baslik=baslik,
        aciklama=aciklama,
        kategori=kategori,
        seviye=seviye,
        video_url="",
        sure_dakika=sure,
        fiyat=fiyat,
        onizleme_metni=onizleme,
        aktif=1
    )
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    print(f"✅ Eğitim eklendi: {baslik} (ID: {yeni.id})")
    return yeni.id

def soru_ekle(db, egitim_id, soru, a, b, c, d, dogru):
    yeni = EgitimSoru(
        egitim_id=egitim_id,
        soru=soru,
        secenek_a=a,
        secenek_b=b,
        secenek_c=c,
        secenek_d=d,
        dogru_cevap=dogru
    )
    db.add(yeni)

def main():
    db = SessionLocal()

    try:
        print("\n🚀 UyumOS Eğitim Modülleri Seed Başlıyor...\n")

        # ==================== EĞİTİM 1: FAI ====================
        fai_id = egitim_ekle(
            db,
            baslik="FAI — İlk Ürün Muayenesi (AS9102)",
            aciklama="AS9102 standardına göre İlk Ürün Muayenesi (FAI) sürecini öğrenin. FAI'nin ne olduğu, ne zaman yapılması gerektiği, form doldurma kuralları, Bubble Drawing ve denetimde karşılaşılan sorunlar.",
            kategori="FAI",
            seviye="orta",
            sure=45,
            fiyat=2500,
            onizleme="FAI'nin ne olduğu, ne zaman yapılması gerektiği, form doldurma kuralları."
        )

        fai_sorular = [
            (
                "Bir KOBİ, 3 yıl önce ürettiği bir parçayı yeniden üretmeye başladı. Makine aynı, operatör aynı, malzeme aynı, çizim aynı. FAI yapmalı mı?",
                "Hayır, hiçbir şey değişmemiş",
                "Evet, 2 yıldan uzun üretim arası olduğu için FAI gerekli",
                "Sadece müşteri isterse yapılmalı",
                "Sadece malzeme değişirse yapılmalı",
                "B"
            ),
            (
                "FAI Form 2'de bir özellik için çizimde 'Ø10 ±0.1' yazıyor. Yapılan ölçüm sonucu 10.05 mm. Form 2'ye ne yazılmalı?",
                "'Uygun'",
                "'10.05'",
                "'10.05 — Uygun'",
                "'Tolerans içinde'",
                "C"
            ),
            (
                "Bir KOBİ, FAI sırasında bir özelliğin tolerans dışı olduğunu gördü (10.15 mm, tolerans ±0.1). Ne yapmalı?",
                "Değeri 10.08 olarak düzeltmeli",
                "Görmezden gelmeli, diğer özellikler uygun",
                "Düzeltici faaliyet açmalı, kök neden analizi yapmalı, süreci düzeltmeli, tekrar FAI yapmalı",
                "Müşteriye bildirmeden parçayı hurdaya ayırmalı",
                "C"
            ),
            (
                "FAI Form 2'de 50 özellik var. KOBİ, 45 özelliği ölçtü, 5'i 'ölçülemedi' diye boş bıraktı. FAI geçerli mi?",
                "Evet, %90 ölçüm yeterli",
                "Hayır, tüm özellikler ölçülmelidir. Ölçülemeyen varsa alternatif yöntem kullanılmalı",
                "Sadece kritik özellikler yeterli",
                "Müşteri kabul ederse geçerli",
                "B"
            ),
            (
                "Bir KOBİ, FAI yaptı ama hammadde sertifikasını (Mill Certificate) eklemedi. Denetimde ne olur?",
                "Hiçbir şey olmaz",
                "FAI eksik kabul edilir, majör uygunsuzluk yazılır",
                "Sadece uyarı alır",
                "Müşteri kabul eder",
                "B"
            ),
            (
                "Bir KOBİ, mevcut bir parçanın sadece yüzey kaplamasını değiştirdi (boya yerine anodize). FAI nasıl yapılmalı?",
                "Tam FAI yapılmalı, tüm özellikler ölçülmeli",
                "Kısmi FAI yapılmalı, sadece yüzey işlem ve etkilenen özellikler doğrulanmalı",
                "FAI gerekmez, sadece boya değişti",
                "Sadece müşteri isterse FAI yapılmalı",
                "B"
            ),
            (
                "FAI raporu kimler tarafından onaylanmalıdır?",
                "Sadece operatör",
                "Kalite yetkilisi + müşteri temsilcisi (sözleşmede belirtilmişse)",
                "Sadece üretim müdürü",
                "Sadece genel müdür",
                "B"
            ),
            (
                "Bir KOBİ, FAI sırasında bir özelliği ölçtü ve sonuç tolerans içinde çıktı. Ancak ölçüm cihazının kalibrasyon süresi 2 ay önce dolmuş. FAI geçerli mi?",
                "Evet, sonuç tolerans içinde",
                "Hayır, kalibrasyonsuz cihazla yapılan ölçüm geçersizdir. FAI tekrarlanmalı",
                "Sadece not düşülür",
                "Müşteri kabul ederse geçerli",
                "B"
            ),
            (
                "FAI belgesi ne kadar süre saklanmalıdır?",
                "1 yıl",
                "3 yıl",
                "Ürün ömrü + sözleşmede belirtilen süre (genellikle 7-10 yıl)",
                "Süresiz",
                "C"
            ),
            (
                "Bir KOBİ, FAI'yi tamamladı ve müşteriye gönderdi. Müşteri, FAI'de bir özelliğin eksik olduğunu fark etti. Ne olur?",
                "Müşteri kabul eder",
                "FAI reddedilir, KOBİ eksik özelliği ölçer, FAI'yi revize eder ve tekrar gönderir",
                "Sadece uyarı alır",
                "FAI iptal edilir",
                "B"
            ),
        ]

        for s in fai_sorular:
            soru_ekle(db, fai_id, s[0], s[1], s[2], s[3], s[4], s[5])

        db.commit()
        print(f"   ✅ {len(fai_sorular)} soru eklendi")

        # ==================== EĞİTİM 2: FOD ====================
        fod_id = egitim_ekle(
            db,
            baslik="FOD — Yabancı Madde Hasarı Önleme (AS9146)",
            aciklama="AS9146 standardına göre Yabancı Madde Hasarı (FOD) önleme programını öğrenin. FOD nedir, nasıl oluşur, önleme yöntemleri, FOD alanları ve denetim gereklilikleri.",
            kategori="FOD",
            seviye="baslangic",
            sure=30,
            fiyat=2000,
            onizleme="FOD nedir, nasıl oluşur, önleme yöntemleri, FOD alanları."
        )

        fod_sorular = [
            (
                "Bir KOBİ'de montaj hattında çalışan operatör, vardiya sonunda alet çantasını kontrol etti ve bir tornavidanın eksik olduğunu fark etti. Ne yapmalı?",
                "Yarın arar, şimdi eve gider",
                "Üretim hattını durdurur, tornavidayı arar, bulunca hattı yeniden başlatır",
                "Yeni tornavida alır, eksik olanı unutur",
                "Vardiya amirine söyler, o arar",
                "B"
            ),
            (
                "Bir KOBİ, AS9100 denetimine hazırlanıyor. Denetçi, FOD alanlarının işaretlenmediğini gördü. Bu bir uygunsuzluk mu?",
                "Hayır, FOD alanı şart değil",
                "Evet, AS9146'ya göre FOD alanları işaretlenmelidir. Majör uygunsuzluk",
                "Sadece uyarı",
                "Müşteri isterse gerekli",
                "B"
            ),
            (
                "Bir KOBİ'de müşteri, ürünün içinde metal talaşı buldu ve ürünü reddetti. KOBİ ne yapmalı?",
                "Ürünü temizleyip tekrar gönderir",
                "Düzeltici faaliyet açar, kök neden analizi yapar, FOD programını gözden geçirir, müşteriye rapor gönderir",
                "Müşteriye 'bir daha olmaz' der",
                "Ürünü hurdaya ayırır, yenisini üretir",
                "B"
            ),
            (
                "Bir KOBİ'de FOD önleme programı var ama personel eğitimi 2 yıl önce yapılmış. Bu uygun mu?",
                "Evet, bir kez eğitim yeterli",
                "Hayır, AS9146'ya göre FOD eğitimi yıllık tekrarlanmalıdır",
                "Sadece yeni çalışanlara eğitim verilmeli",
                "Müşteri isterse eğitim yapılmalı",
                "B"
            ),
            (
                "Bir KOBİ'de üretim alanında çalışan personel, yüzük ve saat takıyor. Bu FOD riski oluşturur mu?",
                "Hayır, kişisel eşya sorun değil",
                "Evet, yüzük ve saat FOD kaynağıdır. Üretim alanında takılmamalıdır",
                "Sadece yüzük sorun, saat sorun değil",
                "Müşteri isterse çıkarılır",
                "B"
            ),
            (
                "Bir KOBİ, FOD alanı olarak sadece montaj hattını belirlemiş. Boyama, taşlama ve paketleme alanları FOD alanı değil. Bu doğru mu?",
                "Evet, sadece montaj FOD alanıdır",
                "Hayır, FOD riski olan tüm alanlar (boyama, taşlama, paketleme, depo) FOD alanı olarak belirlenmelidir",
                "Sadece müşteri isterse",
                "Sadece boyama FOD alanıdır",
                "B"
            ),
            (
                "Bir KOBİ'de FOD kontrolü için 'gölge panosu' (shadow board) kullanılıyor. Bu nedir ve neden önemlidir?",
                "Aletlerin renkli olduğu pano",
                "Her aletin kendi yerinin olduğu, eksik aletin hemen görüldüğü pano",
                "Aletlerin kilitlendiği dolap",
                "Aletlerin atıldığı kutu",
                "B"
            ),
            (
                "Bir KOBİ, ürünü paketlemeden önce FOD kontrolü yapıyor. Ancak paketleme malzemesi (strafor, karton) FOD kaynağı olabilir. Ne yapmalı?",
                "Paketleme malzemesini kontrol etmez",
                "Paketleme malzemesini FOD açısından kontrol eder, temiz malzeme kullanır, müşteri gereksinimlerini karşılar",
                "Sadece straforu kontrol eder",
                "Müşteri isterse kontrol eder",
                "B"
            ),
            (
                "Bir KOBİ, FOD olayı kaydetti (alet düşmesi). Ancak düzeltici faaliyet açmadı. Bu doğru mu?",
                "Evet, kayıt yeterli",
                "Hayır, her FOD olayı için düzeltici faaliyet açılmalı, kök neden analizi yapılmalı",
                "Sadece büyük olaylarda DÖF açılır",
                "Müşteri isterse DÖF açılır",
                "B"
            ),
            (
                "Bir KOBİ, FOD denetimi için iç denetim yapıyor. Ne sıklıkla yapmalı?",
                "5 yılda bir",
                "Yılda en az bir kez + FOD olayı sonrası",
                "Sadece müşteri denetimi öncesi",
                "Hiçbir zaman",
                "B"
            ),
        ]

        for s in fod_sorular:
            soru_ekle(db, fod_id, s[0], s[1], s[2], s[3], s[4], s[5])

        db.commit()
        print(f"   ✅ {len(fod_sorular)} soru eklendi")

        # ==================== EĞİTİM 3: YETEN ====================
        yeten_id = egitim_ekle(
            db,
            baslik="YETEN Portal Yönetimi ve SSB Kriterleri",
            aciklama="SSB'nin YETEN (Yetkinlik ve Teknoloji Değerlendirme) portalının kullanımı. Firma kaydı, ürün kaydı, belge yükleme, güncelleme süreçleri ve SSB kriterleri (idari, mali, teknik) hakkında detaylı eğitim.",
            kategori="YETEN",
            seviye="orta",
            sure=40,
            fiyat=3000,
            onizleme="YETEN portalı kullanımı, SSB kriterleri, EYDEP seviyeleri."
        )

        yeten_sorular = [
            (
                "Bir KOBİ, YETEN'e kayıt olmak istiyor ama AS9100 belgesi yok. YETEN kaydı yapabilir mi?",
                "Hayır, AS9100 zorunlu",
                "Evet, YETEN kaydı için AS9100 zorunlu değil. Ancak teknik kriterlerde AS9100 puan kazandırır",
                "Sadece ISO 9001 yeterli",
                "Müşteri isterse",
                "B"
            ),
            (
                "Bir KOBİ, YETEN'de ürün kaydı yaptı ama 6 ay güncellemedi. Ne olur?",
                "Hiçbir şey olmaz",
                "Ürün bilgileri güncel olmadığı için YETEN'de görünmez, SSB projelerine başvuramaz",
                "Sadece uyarı alır",
                "Kayıt silinir",
                "B"
            ),
            (
                "Bir KOBİ, YETEN'de 'mali kriterler' için son 3 yılın cirosunu girmeli. Ancak firma 2 yıl önce kuruldu. Ne yapmalı?",
                "YETEN'e kayıt olamaz",
                "Mevcut yılların cirosunu girer, 'yeni firma' notu ekler, büyüme planını belirtir",
                "Sahte ciro girer",
                "Sadece son yılın cirosunu girer",
                "B"
            ),
            (
                "Bir KOBİ, YETEN'de 'teknik kriterler' için makine parkını girmeli. Hangi makineleri girmeli?",
                "Sadece yeni makineler",
                "Üretimde kullanılan tüm makineler (CNC, torna, freze, taşlama, ölçüm cihazları)",
                "Sadece CNC makineler",
                "Sadece ithal makineler",
                "B"
            ),
            (
                "Bir KOBİ, YETEN'de 'idari kriterler' için organizasyon şemasını yükledi. Ancak şemada kalite müdürü yok. Bu sorun mu?",
                "Hayır, kalite müdürü şart değil",
                "Evet, AS9100 ve YETEN için kalite müdürü zorunludur. Organizasyon şemasında gösterilmelidir",
                "Sadece büyük firmalarda gerekli",
                "Müşteri isterse",
                "B"
            ),
            (
                "Bir KOBİ, YETEN kaydı yaptı ve EYDEP-D seviyesi aldı. Bu ne anlama gelir?",
                "Firma çok iyi",
                "Firma temel seviyede, gelişmeye açık. EYDEP-C, B, A seviyelerine yükselebilir",
                "Firma başarısız",
                "Firma kara listede",
                "B"
            ),
            (
                "Bir KOBİ, YETEN'de ürün kaydı yaparken 'ürün teknik özellikleri' bölümünü boş bıraktı. Ne olur?",
                "Hiçbir şey olmaz",
                "Ürün eksik kabul edilir, SSB projelerinde değerlendirmeye alınmaz",
                "Sadece uyarı alır",
                "Müşteri kabul eder",
                "B"
            ),
            (
                "Bir KOBİ, YETEN'de 'Ar-Ge yetkinliği'ni göstermek için ne yapmalı?",
                "Hiçbir şey, Ar-Ge şart değil",
                "Ar-Ge projelerini, patentleri, yayınları, Ar-Ge personelini ve laboratuvar altyapısını belgelemeli",
                "Sadece patent göstermeli",
                "Sadece Ar-Ge personeli göstermeli",
                "B"
            ),
            (
                "Bir KOBİ, YETEN kaydı sırasında yanlış bilgi verdi. Tespit edilirse ne olur?",
                "Hiçbir şey olmaz",
                "Firma kara listeye alınır, YETEN kaydı iptal edilir, SSB projelerine başvuramaz",
                "Sadece uyarı alır",
                "Para cezası",
                "B"
            ),
            (
                "Bir KOBİ, YETEN'de EYDEP-B seviyesine yükseldi. KOSGEB'den ne kadar kredi alabilir?",
                "10 milyon TL",
                "20 milyon TL",
                "27,5 milyon TL",
                "30 milyon TL",
                "C"
            ),
        ]

        for s in yeten_sorular:
            soru_ekle(db, yeten_id, s[0], s[1], s[2], s[3], s[4], s[5])

        db.commit()
        print(f"   ✅ {len(yeten_sorular)} soru eklendi")

        print("\n🎉 Seed tamamlandı!")
        print(f"📊 Toplam: 3 eğitim, 30 soru\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Hata: {e}\n")
    finally:
        db.close()

if __name__ == "__main__":
    main()