async function formuGonder() {
    const form = document.getElementById('assessmentForm');
    const formData = new FormData(form);
    let cevaplar = {};
    let cevaplananSoru = 0;

    // Şirket adı kontrolü
    const sirketAdi = document.getElementById('sirketAdi').value.trim();
    if (!sirketAdi) {
        document.getElementById('sonuc').innerHTML = 
            '<div style="color: #ef4444;">Lütfen şirket adınızı girin.</div>';
        return;
    }

    // Kullanıcı email'ini localStorage'dan al
    let kullaniciEmail = "";
    try {
        const kullaniciStr = localStorage.getItem('kullanici');
        if (kullaniciStr) {
            kullaniciEmail = JSON.parse(kullaniciStr).email || "";
        }
    } catch (e) {
        console.error("localStorage hatası:", e);
    }

    // Cevapları topla
    for (let i = 1; i <= 70; i++) {
        const cevap = formData.get('soru' + i);
        if (cevap !== null) {
            cevaplar['soru' + i] = parseInt(cevap);
            cevaplananSoru++;
        }
    }

    // Tüm sorular cevaplanmış mı?
    if (cevaplananSoru < 70) {
        document.getElementById('sonuc').innerHTML = 
            '<div style="color: #ef4444;">Lütfen tüm soruları cevaplayın. (' + 
            cevaplananSoru + '/70)</div>';
        return;
    }

    // Yükleniyor mesajı
    document.getElementById('sonuc').innerHTML = 
        '<div style="color: #a8c5e0;">Kaydediliyor...</div>';

    try {
        const response = await fetch('/degerlendirme', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sirket_adi: sirketAdi,
                kullanici_email: kullaniciEmail,
                cevaplar: cevaplar
            })
        });

        const data = await response.json();

        // Hata kontrolü
        if (!response.ok) {
            document.getElementById('sonuc').innerHTML = 
                '<div style="color: #ef4444; padding: 20px; background: rgba(239,68,68,0.1); border-radius: 10px; text-align: center;">' +
                '❌ ' + (data.detail || 'Bir hata oluştu.') + '</div>';
            return;
        }

        const kayit = data.kayit;

        if (!kayit) {
            document.getElementById('sonuc').innerHTML = 
                '<div style="color: #ef4444; padding: 20px; background: rgba(239,68,68,0.1); border-radius: 10px; text-align: center;">' +
                '❌ Sunucudan beklenmeyen bir cevap geldi.</div>';
            return;
        }

        // Renk ve mesaj belirleme
        let renk = '#ef4444';
        let mesaj = 'Kritik eksikleriniz var. Danışmanlık gerekli.';
        
        if (kayit.yuzde >= 70) {
            renk = '#4ade80';
            mesaj = 'İyi durumdasınız. Küçük eksikler var.';
        } else if (kayit.yuzde >= 40) {
            renk = '#fbbf24';
            mesaj = 'Orta seviyedesiniz. Bazı kritik eksikler var.';
        }

        // Sonuç HTML'i
        let html = '';
        html += '<div style="color: ' + renk + '; font-size: 24px; font-weight: bold;">';
        html += kayit.sirket_adi + ' — AS9100/EYDEP Hazırlık Skoru: %' + kayit.yuzde;
        html += '</div>';
        html += '<div style="color: #a8c5e0; margin-top: 10px;">' + mesaj + '</div>';
        html += '<div style="margin-top: 20px; padding: 20px; background: rgba(255,255,255,0.05); border-radius: 10px;">';
        html += '<strong>Toplam Puan:</strong> ' + kayit.toplam_puan + ' / ' + kayit.maksimum_puan;
        html += '<br><strong>Kayıt ID:</strong> ' + kayit.id;
        html += '</div>';

        // Gap raporu butonu
        html += '<div style="margin-top: 25px; text-align: center;">';
        html += '<a href="gap-raporu.html?id=' + kayit.id + '" ';
        html += 'style="display: inline-block; background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%); ';
        html += 'color: white; padding: 15px 35px; border-radius: 50px; text-decoration: none; ';
        html += 'font-size: 16px; font-weight: 600; box-shadow: 0 10px 30px rgba(0,180,216,0.3);">';
        html += '📊 Gap Raporunu Görüntüle →</a>';
        html += '<div style="color: #6b8ba3; font-size: 13px; margin-top: 10px;">';
        html += 'Detaylı 7 kategori analizi ve PDF çıktısı için tıklayın';
        html += '</div>';
        html += '</div>';

        document.getElementById('sonuc').innerHTML = html;

    } catch (error) {
        document.getElementById('sonuc').innerHTML = 
            '<div style="color: #ef4444; padding: 20px; background: rgba(239,68,68,0.1); border-radius: 10px; text-align: center;">' +
            '❌ Bağlantı hatası: ' + error.message + '</div>';
    }
}