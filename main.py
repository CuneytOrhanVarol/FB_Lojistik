import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- VERİTABANI BAĞLANTISI ---
conn = sqlite3.connect('fb_operasyon_merkezi_v2.db', check_same_thread=False)
c = conn.cursor()

# Tabloları Başlat
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

    # --- 1. SİPARİŞ TAKİP VE TOPLU GÜNCELLEME ---
    if secim == "Sipariş Takip / Operasyon":
        st.header("Sipariş Takip ve Operasyon Paneli")
        
        query = "SELECT id as 'ID', sicil_no as 'Sicil No', uye_adi as 'Ad Soyad', urunler as 'Ürünler', adet as 'Adet', durum as 'Durum', kargo_no as 'Kargo No', kargo_tarihi as 'Kargo Tarihi' FROM siparisler ORDER BY id DESC"
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.divider()
            
            st.subheader("🛠️ Toplu veya Tekil Güncelleme")
            with st.form("güncelleme_formu"):
                col1, col2 = st.columns(2)
                secilen_id_listesi = col1.multiselect("Güncellenecek ID'leri Seçin", df['ID'].tolist())
                yeni_statü = col2.selectbox("Yeni Durum Seçin", DURUMLAR)
                
                col3, col4 = st.columns(2)
                yeni_kargo_no = col3.text_input("Kargo No (Opsiyonel)")
                yeni_kargo_tarih = col4.text_input("Kargo Tarihi (Örn: 26.01.2024)")
                
                update_button = st.form_submit_button("Seçili Kayıtları Güncelle")
                
                if update_button:
                    if not secilen_id_listesi:
                        st.warning("Lütfen güncellenecek en az bir ID seçin.")
                    else:
                        for s_id in secilen_id_listesi:
                            c.execute("""UPDATE siparisler SET durum = ?, kargo_no = ?, kargo_tarihi = ? WHERE id = ?""", 
                                      (yeni_statü, yeni_kargo_no, yeni_kargo_tarih, s_id))
                        conn.commit()
                        log_ekle(mevcut_user, f"ID {secilen_id_listesi} kayıtlarını '{yeni_statü}' olarak toplu güncelledi.")
                        st.success("Seçilen kayıtlar başarıyla güncellendi!")
                        st.rerun()
        else:
            st.info("Sistemde henüz sipariş bulunmuyor.")

    # --- 2. YENİ KAYIT & İÇERİ AKTAR ---
    elif secim == "Yeni Kayıt & İçeri Aktar":
        t1, t2 = st.tabs(["✍️ Tek Tek Ekle", "📂 Excel/CSV Yükle"])
        with t1:
            with st.form("tekil"):
                f_sicil = st.text_input("Sicil No")
                f_ad = st.text_input("Ad Soyad")
                f_urun = st.text_area("Ürünler (Virgülle ayırın)")
                f_adet = st.number_input("Adet", min_value=1, value=1)
                if st.form_submit_button("Kaydet"):
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, urunler, adet, durum, tarih) VALUES (?,?,?,?,?,?)",
                              (f_sicil, f_ad, f_urun, f_adet, "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y")))
                    conn.commit()
                    log_ekle(mevcut_user, f"Yeni kayıt: {f_ad}")
                    st.success("Eklendi!")
        with t2:
            st.write("Sütunlar: **sicil_no, uye_adi, urunler, adet**")
            up_file = st.file_uploader("Dosya Seç", type=['xlsx', 'csv'])
            if up_file:
                df_up = pd.read_excel(up_file) if up_file.name.endswith('xlsx') else pd.read_csv(up_file)
                if st.button("Aktarımı Başlat"):
                    for _, r in df_up.iterrows():
                        c.execute("INSERT INTO siparisler (sicil_no, uye_adi, urunler, adet, durum, tarih) VALUES (?,?,?,?,?,?)",
                                  (str(r['sicil_no']), str(r['uye_adi']), str(r['urunler']), int(r.get('adet', 1)), "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y")))
                    conn.commit()
                    st.success("Aktarıldı!")
                    st.rerun()

    # --- 3. KAYIT SİLME (SADECE YÖNETİCİ) ---
    elif secim == "Kayıt Silme İşlemleri":
        if st.session_state['yetki'] == "Yönetici":
            st.header("🗑️ Kayıt Silme Paneli")
            df_sil = pd.read_sql_query("SELECT id, sicil_no, uye_adi FROM siparisler", conn)
            silinecek_id = st.multiselect("Silinecek Siparişleri Seçin", df_sil['id'].tolist())
            if st.button("Seçili Kayıtları Kalıcı Olarak Sil"):
                if silinecek_id:
                    for s_id in silinecek_id:
                        c.execute("DELETE FROM siparisler WHERE id = ?", (s_id,))
                    conn.commit()
                    log_ekle(mevcut_user, f"ID {silinecek_id} kayıtlarını sildi.")
                    st.error("Kayıtlar silindi!")
                    st.rerun()
        else:
            st.warning("Bu alanı sadece yöneticiler kullanabilir.")

    # --- 4. LOG VE EXCEL ---
    elif secim == "İşlem Geçmişi (Log)":
        st.dataframe(pd.read_sql_query("SELECT zaman, kullanici, islem FROM islem_gecmisi ORDER BY id DESC", conn), use_container_width=True)

    elif secim == "Dışarı Aktar":
        df_out = pd.read_sql_query("SELECT * FROM siparisler", conn)
        st.download_button("Excel İndir", df_out.to_csv(index=False).encode('utf-8-sig'), "fb_export.csv", "text/csv")

    if st.sidebar.button("Çıkış"):
        del st.session_state['kullanici']
        st.rerun()
