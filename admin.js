window.addEventListener('DOMContentLoaded', () => {
    const kullaniciStr = localStorage.getItem('kullanici');
    if (!kullaniciStr) {
        window.location.href = 'giris.html';
        return;
    }

    try {
        const kullanici = JSON.parse(kullaniciStr);
        if (kullanici.rol !== 'admin') {
            alert('Bu sayfaya erişim yetkiniz yok');
            window.location.href = 'panel.html';
            return;
        }
    } catch (e) {
        window.location.href = 'giris.html';
        return;
    }

    ozetYukle();
    sekmeGoster('kullanicilar', document.querySelector('.tab-btn'));
});

async function ozetYukle() {
    try {
        const response = await fetch('http://127.0.0.1:8000/admin/ozet');
        const data = await response.json();
        document.getElementById('toplamKullanici').textContent = data.toplam_kullanici;
        document.getElementById('toplamAssessment').textContent = data.toplam_assessment;
        document.getElementById('toplamTalep').textContent = data.toplam_talep;
        document.getElementById('bekleyenTalep').textContent = data.bekleyen_talep;
    } catch (e) {
        console.error(e);
    }
}

async function sekmeGoster(tip, btn) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const icerik = document.getElementById('tabIcerik');
    icerik.innerHTML = 'Yükleniyor...';

    try {
        if (tip === 'kullanicilar') {
            const r = await fetch('http://127.0.0.1:8000/admin/kullanicilar');
            const data = await r.json();
            kullanicilariGoster(data);
        } else if (tip === 'assessmentlar') {
            const r = await fetch('http://127.0.0.1:8000/admin/tum-assessmentlar');
            const data = await r.json();
            assessmentlariGoster(data);
        } else if (tip === 'talepler') {
            const r = await fetch('http://127.0.0.1:8000/danismanlik-talepleri');
            const data = await r.json();
            talepleriGoster(data);
        }
    } catch (e) {
        icerik.innerHTML = '<div style="color: #ef4444;">Hata: ' + e.message + '</div>';
    }
}

function kullanicilariGoster(data) {
    if (data.toplam === 0) {
        document.getElementById('tabIcerik').innerHTML = '<p style="color: #a8c5e0;">Henüz kullanıcı yok.</p>';
        return;
    }

    let html = '<table class="veri-tablo"><thead><tr><th>ID</th><th>Şirket</th><th>E-posta</th><th>Rol</th><th>Kayıt Tarihi</th></tr></thead><tbody>';
    data.kullanicilar.forEach(k => {
        const tarih = new Date(k.olusturma_tarihi).toLocaleDateString('tr-TR');
        const rolRenk = k.rol === 'admin' ? '#ef4444' : '#00b4d8';
        html += '<tr>';
        html += '<td>' + k.id + '</td>';
        html += '<td>' + k.sirket_adi + '</td>';
        html += '<td>' + k.email + '</td>';
        html += '<td style="color: ' + rolRenk + '; font-weight: bold;">' + k.rol + '</td>';
        html += '<td>' + tarih + '</td>';
        html += '</tr>';
    });
    html += '</tbody></table>';
    document.getElementById('tabIcerik').innerHTML = html;
}

function assessmentlariGoster(data) {
    if (data.toplam === 0) {
        document.getElementById('tabIcerik').innerHTML = '<p style="color: #a8c5e0;">Henüz assessment yok.</p>';
        return;
    }

    let html = '<table class="veri-tablo"><thead><tr><th>ID</th><th>Şirket</th><th>E-posta</th><th>Skor</th><th>Tarih</th><th></th></tr></thead><tbody>';
    data.kayitlar.forEach(k => {
        const tarih = new Date(k.olusturma_tarihi).toLocaleDateString('tr-TR', {
            year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
        let skorSinif = 'skor-orta';
        if (k.yuzde >= 70) skorSinif = 'skor-iyi';
        else if (k.yuzde < 40) skorSinif = 'skor-zayif';

        html += '<tr>';
        html += '<td>' + k.id + '</td>';
        html += '<td>' + k.sirket_adi + '</td>';
        html += '<td>' + (k.kullanici_email || '—') + '</td>';
        html += '<td class="' + skorSinif + '">%' + k.yuzde + '</td>';
        html += '<td>' + tarih + '</td>';
        html += '<td><a href="gap-raporu.html?id=' + k.id + '" style="color: #00b4d8;">Rapor →</a></td>';
        html += '</tr>';
    });
    html += '</tbody></table>';
    document.getElementById('tabIcerik').innerHTML = html;
}

function talepleriGoster(data) {
    if (data.toplam === 0) {
        document.getElementById('tabIcerik').innerHTML = '<p style="color: #a8c5e0;">Henüz danışmanlık talebi yok.</p>';
        return;
    }

    let html = '<table class="veri-tablo"><thead><tr><th>ID</th><th>Şirket</th><th>E-posta</th><th>Telefon</th><th>Mesaj</th><th>Durum</th><th>Tarih</th></tr></thead><tbody>';
    data.talepler.forEach(t => {
        const tarih = new Date(t.olusturma_tarihi).toLocaleDateString('tr-TR', {
            year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
        html += '<tr>';
        html += '<td>' + t.id + '</td>';
        html += '<td>' + t.sirket_adi + '</td>';
        html += '<td>' + t.email + '</td>';
        html += '<td>' + t.telefon + '</td>';
        html += '<td>' + (t.mesaj || '—') + '</td>';
        html += '<td class="durum-' + t.durum + '">' + t.durum + '</td>';
        html += '<td>' + tarih + '</td>';
        html += '</tr>';
    });
    html += '</tbody></table>';
    document.getElementById('tabIcerik').innerHTML = html;
}

function cikisYap() {
    localStorage.removeItem('token');
    localStorage.removeItem('kullanici');
    window.location.href = 'giris.html';
}