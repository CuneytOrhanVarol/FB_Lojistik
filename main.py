import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- VERİTABANI BAĞLANTISI ---
conn = sqlite3.connect('fb_operasyon_merkezi.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS siparisler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uye_adi TEXT, sicil_no TEXT, urunler TEXT, tisort_beden TEXT, 
    durum TEXT, kargo_no TEXT, tarih TEXT, notlar TEXT)''')

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
    if st.button("Giriş"):
        if KULLANICILAR[user] == sifre:
            st.session_state['kullanici'] = user
            st.session_state['yetki'] = "Yönetici" if user in YONETICILER else "Tedarikçi"
            log_ekle(user, "Sisteme giriş yaptı")
            st.rerun()
        else:
            st.error("Hatalı şifre!")
else:
    mevcut_user = st.session_state['kullanici']
    st.sidebar.title(f"Hoş geldin, {mevcut_user}")
    secim = st.sidebar.radio("Menü", ["Sipariş Takip / Operasyon", "Yeni Kayıt & İçeri Aktar", "İşlem Geçmişi (Log)", "Dışarı Aktar (Excel)"])

    # --- 1. SİPARİŞ TAKİP (GELİŞMİŞ TABLO GÖRÜNÜMÜ) ---
    if secim == "Sipariş Takip / Operasyon":
        st.header("Operasyon İzleme Ekranı")
        
        # Verileri çek
        df = pd.read_sql_query("SELECT id, sicil_no, uye_adi, urunler, durum, kargo_no, tarih FROM siparisler ORDER BY id DESC", conn)
        
        if not df.empty:
            # Tabloyu göster
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("Durum Güncelleme")
            
            # Güncelleme Formu
            with st.expander("Seçili Siparişi Güncelle"):
                col1, col2, col3 = st.columns(3)
                secilen_id = col1.selectbox("Sipariş ID (En soldaki numara)", df['id'].tolist())
                yeni_statü = col2.selectbox("Yeni Durum", ["Sipariş Alındı", "Tedarik: Rozet (Engin B.)", "Tedarik: Plaket (Mevlüt B.)", "İpek Kutu'ya Sevk Edildi", "Kargoda", "Tamamlandı"])
                kargo_input = col3.text_input("Kargo No (Kargodaysa girin)")
                
                if st.button("Durumu Kaydet"):
                    c.execute("UPDATE siparisler SET durum = ?, kargo_no = ? WHERE id = ?", (yeni_statü, kargo_input, secilen_id))
                    conn.commit()
                    log_ekle(mevcut_user, f"ID:{secilen_id} durumunu '{yeni_statü}' yaptı.")
                    st.success("Güncellendi!")
                    st.rerun()
        else:
            st.info("Henüz kayıtlı sipariş bulunmuyor.")

    # --- 2. YENİ KAYIT & İÇERİ AKTAR ---
    elif secim == "Yeni Kayıt & İçeri Aktar":
        tab1, tab2 = st.tabs(["Tekil Kayıt", "Toplu İçeri Aktar (Excel/CSV)"])
        
        with tab1:
            with st.form("tekil_form"):
                u_ad = st.text_input("Ad Soyad")
                u_sicil = st.text_input("Sicil No")
                u_urun = st.multiselect("Ürünler", ["Üyelik Kiti", "Üyelik Kartı", "Üyelik Sertifikası", "Üyelik Rozeti", "Üyelik Tişörtü", "Kutu ve Cam Kristal Plaket"])
                u_submit = st.form_submit_button("Siparişi Ekle")
                if u_submit:
                    tarih = datetime.now().strftime("%d/%m/%Y")
                    c.execute("INSERT INTO siparisler (uye_adi, sicil_no, urunler, durum, tarih) VALUES (?,?,?,?,?)",
                              (u_ad, u_sicil, ", ".join(u_ad), "Sipariş Alındı", tarih))
                    conn.commit()
                    log_ekle(mevcut_user, f"Yeni sipariş eklendi: {u_ad}")
                    st.success("Kaydedildi!")

        with tab2:
            st.info("Excel dosyanızda 'sicil_no', 'uye_adi', 'urunler' sütunları olmalıdır.")
            uploaded_file = st.file_uploader("Dosya Seçin", type=['xlsx', 'csv'])
            if uploaded_file:
                df_upload = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
                st.write("Yüklenecek Veri Önizlemesi:")
                st.dataframe(df_upload.head())
                if st.button("Tümünü Sisteme Aktar"):
                    for _, row in df_upload.iterrows():
                        tarih = datetime.now().strftime("%d/%m/%Y")
                        c.execute("INSERT INTO siparisler (uye_adi, sicil_no, urunler, durum, tarih) VALUES (?,?,?,?,?)",
                                  (str(row['uye_adi']), str(row['sicil_no']), str(row['urunler']), "Sipariş Alındı", tarih))
                    conn.commit()
                    log_ekle(mevcut_user, "Excel ile toplu yükleme yapıldı.")
                    st.success("Tüm veriler başarıyla aktarıldı!")

    # --- DİĞER MENÜLER (Görüntüleme) ---
    elif secim == "İşlem Geçmişi (Log)":
        st.header("Sistem Hareketleri")
        log_df = pd.read_sql_query("SELECT * FROM islem_gecmisi ORDER BY id DESC", conn)
        st.dataframe(log_df, use_container_width=True)

    elif secim == "Dışarı Aktar (Excel)":
        st.header("Verileri Dışarı Aktar")
        full_df = pd.read_sql_query("SELECT * FROM siparisler", conn)
        st.download_button("Excel/CSV İndir", full_df.to_csv(index=False).encode('utf-8-sig'), "fb_export.csv", "text/csv")

    if st.sidebar.button("Güvenli Çıkış"):
        del st.session_state['kullanici']
        st.rerun()
