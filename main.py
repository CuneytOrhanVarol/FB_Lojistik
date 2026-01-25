import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- VERİTABANI VE GÜVENLİK ---
conn = sqlite3.connect('fb_operasyon_merkezi.db', check_same_thread=False)
c = conn.cursor()

# Tabloları Oluştur (Siparişler ve Log/Geçmiş Tablosu)
c.execute('''CREATE TABLE IF NOT EXISTS siparisler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uye_adi TEXT, sicil_no TEXT, urunler TEXT, tisort_beden TEXT, 
    durum TEXT, kargo_no TEXT, tarih TEXT, notlar TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS islem_gecmisi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici TEXT, islem TEXT, zaman TEXT)''')
conn.commit()

# --- KULLANICI TANIMLAMALARI ---
KULLANICILAR = {
    "Cüneyt Orhan Varol": "fb01",
    "Mehmet Erkin Ataş": "fb02",
    "Ersen Avcı": "fb03",
    "Simay Önder": "fb04",
    "Pervin Hanım": "ipek123",
    "Mevlüt Bey": "ikba456",
    "Engin Bey": "kuker789"
}

YONETICILER = ["Cüneyt Orhan Varol", "Mehmet Erkin Ataş", "Ersen Avcı", "Simay Önder"]

# --- FONKSİYONLAR ---
def log_ekle(kullanici, islem):
    zaman = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    c.execute("INSERT INTO islem_gecmisi (kullanici, islem, zaman) VALUES (?,?,?)", (kullanici, islem, zaman))
    conn.commit()

# --- ARAYÜZ ---
st.set_page_config(page_title="FB Kongre Operasyon", layout="wide")

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
    
    menü = ["Sipariş Takip / Operasyon"]
    if st.session_state['yetki'] == "Yönetici":
        menü.extend(["Yeni Sipariş Girişi", "İşlem Geçmişi (Log)", "Excel Rapor"])
    
    secim = st.sidebar.radio("Menü", menü)

    # --- 1. SİPARİŞ TAKİP (TÜM KULLANICILAR) ---
    if secim == "Sipariş Takip / Operasyon":
        st.header("Siparişler ve Durum Yönetimi")
        df = pd.read_sql_query("SELECT * FROM siparisler", conn)
        
        for idx, row in df.iterrows():
            with st.expander(f"{row['uye_adi']} - {row['durum']}"):
                col1, col2 = st.columns(2)
                
                # Durum Güncelleme
                yeni_durum = col1.selectbox("Statü Değiştir", 
                    ["Sipariş Alındı", "Tedarik: Rozet Bekleniyor (Engin B.)", "Tedarik: Plaket Bekleniyor (Mevlüt B.)", 
                     "İpek Kutu'ya Sevk Edildi", "Kargoya Verildi", "Tamamlandı"],
                    index=0, key=f"d_{row['id']}")
                
                kargo = col2.text_input("Kargo No", value=row['kargo_no'] if row['kargo_no'] else "", key=f"k_{row['id']}")
                
                if st.button("Güncelle", key=f"b_{row['id']}"):
                    c.execute("UPDATE siparisler SET durum = ?, kargo_no = ? WHERE id = ?", (yeni_durum, kargo, row['id']))
                    log_ekle(mevcut_user, f"{row['uye_adi']} siparişini '{yeni_durum}' yaptı.")
                    st.success("Güncellendi!")
                    st.rerun()

    # --- 2. YENİ SİPARİŞ (SADECE YÖNETİCİ) ---
    elif secim == "Yeni Sipariş Girişi":
        st.header("Yeni Üye Siparişi Oluştur")
        with st.form("yeni_sip"):
            uye = st.text_input("Üye Ad Soyad")
            sicil = st.text_input("Sicil No")
            urunler = st.multiselect("Ürünler", ["Üyelik Kiti", "Üyelik Kartı", "Üyelik Sertifikası", "Üyelik Rozeti", "Üyelik Tişörtü", "Kutu ve Cam Kristal Plaket"])
            submit = st.form_submit_button("Kaydet")
            if submit:
                tarih = datetime.now().strftime("%d/%m/%Y")
                c.execute("INSERT INTO siparisler (uye_adi, sicil_no, urunler, durum, tarih) VALUES (?,?,?,?,?)",
                          (uye, sicil, ", ".join(urunler), "Sipariş Alındı", tarih))
                log_ekle(mevcut_user, f"Yeni sipariş girdi: {uye}")
                st.success("Kayıt başarılı!")

    # --- 3. İŞLEM GEÇMİŞİ (LOG - SADECE YÖNETİCİ) ---
    elif secim == "İşlem Geçmişi (Log)":
        st.header("Sistemdeki Tüm Hareketler")
        log_df = pd.read_sql_query("SELECT * FROM islem_gecmisi ORDER BY id DESC", conn)
        st.table(log_df)

    # --- 4. EXCEL (SADECE YÖNETİCİ) ---
    elif secim == "Excel Rapor":
        df = pd.read_sql_query("SELECT * FROM siparisler", conn)
        st.download_button("Excel İndir", df.to_csv(index=False).encode('utf-8-sig'), "fb_rapor.csv", "text/csv")

    if st.sidebar.button("Çıkış Yap"):
        del st.session_state['kullanici']
        st.rerun()
