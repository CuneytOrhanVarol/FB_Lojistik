import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# --- VERİTABANI BAĞLANTISI ---
conn = sqlite3.connect('fb_operasyon_merkezi_v2.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS siparisler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sicil_no TEXT, uye_adi TEXT, urunler TEXT, adet INTEGER DEFAULT 1,
    durum TEXT, kargo_no TEXT, kargo_tarihi TEXT, tarih TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS islem_gecmisi (
    id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici TEXT, islem TEXT, zaman TEXT)''')
conn.commit()

# --- KULLANICI VE YETKİ ---
KULLANICILAR = {
    "Cüneyt Orhan Varol": "fb01", "Mehmet Erkin Ataş": "fb02", 
    "Ersen Avcı": "fb03", "Simay Önder": "fb04",
    "Pervin Hanım": "ipek123", "Mevlüt Bey": "ikba456", "Engin Bey": "kuker789"
}
YONETICILER = ["Cüneyt Orhan Varol", "Mehmet Erkin Ataş", "Ersen Avcı", "Simay Önder"]
DURUMLAR = ["Hazırlanıyor", "Kuker hazırlıyor", "İKBA Kristal hazırlıyor", "İpek Kutu'ya gönderildi", "Kargoda", "Kulüpten Teslim", "Tamamlandı"]

def log_ekle(kullanici, islem):
    zaman = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    c.execute("INSERT INTO islem_gecmisi (kullanici, islem, zaman) VALUES (?,?,?)", (kullanici, islem, zaman))
    conn.commit()

# --- ARAYÜZ ---
st.set_page_config(page_title="FB Kongre Lojistik Paneli", layout="wide")

if 'kullanici' not in st.session_state:
    st.title("FB Operasyon Merkezi Giriş")
    user = st.selectbox("Kullanıcı Seçin", list(KULLANICILAR.keys()))
    sifre = st.text_input("Şifre", type="password")
    if st.button("Sisteme Giriş Yap"):
        if KULLANICILAR.get(user) == sifre:
            st.session_state['kullanici'] = user
            st.session_state['yetki'] = "Yönetici" if user in YONETICILER else "Tedarikçi"
            log_ekle(user, "Sisteme giriş yaptı")
            st.rerun()
        else:
            st.error("Hatalı şifre!")
else:
    mevcut_user = st.session_state['kullanici']
    if st.sidebar.button("🔄 Verileri Yenile"):
        st.rerun()
        
    st.sidebar.title(f"Hoş geldin, {mevcut_user}")
    secim = st.sidebar.radio("Menü", ["Sipariş Takip / Operasyon", "Yeni Kayıt & İçeri Aktar", "Kayıt Silme İşlemleri", "İşlem Geçmişi (Log)", "Dışarı Aktar"])

    if secim == "Sipariş Takip / Operasyon":
        st.header("🔎 Detaylı ve Toplu Arama Paneli")
        
        with st.expander("🔍 Gelişmiş Filtreleme (Tekli veya Toplu)", expanded=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                search_id = st.text_input("ID'ye göre ara")
                search_name = st.text_input("İsim Soyad'a göre ara")
                search_status = st.selectbox("Durum Filtrele", ["Tümü"] + DURUMLAR)
            with c2:
                search_sicil_bulk = st.text_area("Toplu Sicil No Sorgulama (Sicilleri alt alta veya virgülle ayırarak yapıştırın)")
            search_btn = st.button("Kayıtları Filtrele / Getir")

        query = """SELECT id as 'ID', sicil_no as 'Sicil No', uye_adi as 'Ad Soyad', 
                   urunler as 'Ürünler', adet as 'Adet', durum as 'Durum', 
                   kargo_no as 'Kargo No', kargo_tarihi as 'Kargo Tarihi', tarih as 'Kayıt Tarihi' 
                   FROM siparisler WHERE 1=1"""
        params = []
        
        if search_id:
            query += " AND id = ?"
            params.append(search_id)
        if search_sicil_bulk:
            siciller = [s.strip() for s in search_sicil_bulk.replace('\n', ',').split(',') if s.strip()]
            if siciller:
                placeholders = ','.join(['?'] * len(siciller))
                query += f" AND sicil_no IN ({placeholders})"
                params.extend(siciller)
        if search_name:
            query += " AND uye_adi LIKE ?"
            params.append(f"%{search_name}%")
        if search_status != "Tümü":
            query += " AND durum = ?"
            params.append(search_status)
            
        query += " ORDER BY id DESC"
        df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            st.subheader(f"📋 Listelenen Siparişler ({len(df)} Kayıt)")
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.divider()
            
            st.subheader("🛠️ Toplu veya Tekil Güncelleme")
            df['secim_etiketi'] = df['Sicil No'].astype(str) + " - " + df['Ad Soyad'] + " (ID: " + df['ID'].astype(str) + ")"
            etiket_to_id = dict(zip(df['secim_etiketi'], df['ID']))
            
            with st.form("güncelleme_formu"):
                col1, col2 = st.columns(2)
                secilen_etiketler = col1.multiselect("Güncellenecek Kayıtları Seçin", df['secim_etiketi'].tolist())
                yeni_statü = col2.selectbox("Yeni Durum Seçin", DURUMLAR)
                col3, col4 = st.columns(2)
                yeni_kargo_no = col3.text_input("Kargo No")
                yeni_kargo_tarih = col4.text_input("Kargo Tarihi")
                
                if st.form_submit_button("Seçili Kayıtları Güncelle"):
                    if secilen_etiketler:
                        ids = [etiket_to_id[e] for e in secilen_etiketler]
                        for s_id in ids:
                            c.execute("UPDATE siparisler SET durum = ?, kargo_no = ?, kargo_tarihi = ? WHERE id = ?", (yeni_statü, yeni_kargo_no, yeni_kargo_tarih, s_id))
                        conn.commit()
                        log_ekle(mevcut_user, f"{len(ids)} kaydı '{yeni_statü}' olarak güncelledi.")
                        st.success("Başarıyla güncellendi!")
                        st.rerun()
        else:
            st.warning("Aranan kriterlerde kayıt bulunamadı.")

    elif secim == "Yeni Kayıt & İçeri Aktar":
        t1, t2 = st.tabs(["✍️ Tekil Kayıt", "📂 Excel Yükle"])
        with t1:
            with st.form("tekil"):
                f_sicil = st.text_input("Sicil No")
                f_ad = st.text_input("Ad Soyad")
                f_urun = st.text_area("Ürünler")
                f_adet = st.number_input("Adet", min_value=1, value=1)
                if st.form_submit_button("Kaydet"):
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, urunler, adet, durum, tarih) VALUES (?,?,?,?,?,?)",
                              (f_sicil, f_ad, f_urun, f_adet, "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y")))
                    conn.commit()
                    log_ekle(mevcut_user, f"Yeni kayıt: {f_ad}")
                    st.success("Eklendi!")
        with t2:
            st.info("Sütunlar: sicil_no, uye_adi, urunler, adet")
            up_file = st.file_uploader("Excel Seç", type=['xlsx'])
            if up_file:
                df_up = pd.read_excel(up_file)
                if st.button("Aktarımı Başlat"):
                    for _, r in df_up.iterrows():
                        c.execute("INSERT INTO siparisler (sicil_no, uye_adi, urunler, adet, durum, tarih) VALUES (?,?,?,?,?,?)",
                                  (str(r['sicil_no']), str(r['uye_adi']), str(r['urunler']), int(r.get('adet', 1)), "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y")))
                    conn.commit()
                    st.success("Başarıyla aktarıldı!")
                    st.rerun()

    elif secim == "Kayıt Silme İşlemleri":
        if st.session_state['yetki'] == "Yönetici":
            st.header("🗑️ Kayıt Silme Paneli")
            df_sil = pd.read_sql_query("SELECT id, sicil_no, uye_adi FROM siparisler", conn)
            df_sil['etiket'] = df_sil['sicil_no'].astype(str) + " - " + df_sil['uye_adi']
            etiket_dict = dict(zip(df_sil['etiket'], df_sil['id']))
            secilenler = st.multiselect("Silinecekleri Seç", df_sil['etiket'].tolist())
            if st.button("Seçilenleri Sil"):
                for e in secilenler:
                    c.execute("DELETE FROM siparisler WHERE id = ?", (etiket_dict[e],))
                conn.commit()
                log_ekle(mevcut_user, f"{len(secilenler)} kayıt sildi.")
                st.error("Kayıtlar silindi!")
                st.rerun()
            st.divider()
            st.subheader("🔥 Tüm Veritabanını Temizle")
            onay_kutu = st.checkbox("Tüm kayıtları silmek istediğime eminim.")
            if st.button("TÜM SİPARİŞLERİ SİL"):
                if onay_kutu:
                    c.execute("DELETE FROM siparisler")
                    conn.commit()
                    log_ekle(mevcut_user, "TÜM VERİTABANINI SIFIRLADI!")
                    st.error("Tüm kayıtlar silindi!")
                    st.rerun()
        else:
            st.warning("Bu alanı sadece yöneticiler kullanabilir.")

    elif secim == "Dışarı Aktar":
        st.header("📊 Verileri Excel Olarak İndir")
        df_out = pd.read_sql_query("SELECT * FROM siparisler", conn)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_out.to_excel(writer, index=False, sheet_name='Siparişler')
        st.download_button("📥 Excel İndir", output.getvalue(), f"fb_lojistik_{datetime.now().strftime('%Y%m%d')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    elif secim == "İşlem Geçmişi (Log)":
        st.dataframe(pd.read_sql_query("SELECT zaman, kullanici, islem FROM islem_gecmisi ORDER BY id DESC", conn), use_container_width=True)

    if st.sidebar.button("Güvenli Çıkış"):
        del st.session_state['kullanici']
        st.rerun()
