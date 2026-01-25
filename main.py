import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- VERİTABANI BAĞLANTISI ---
conn = sqlite3.connect('fb_operasyon_merkezi.db', check_same_thread=False)
c = conn.cursor()

# Tabloları Başlat
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
    if st.button("Sisteme Giriş Yap"):
        if KULLANICILAR[user] == sifre:
            st.session_state['kullanici'] = user
            st.session_state['yetki'] = "Yönetici" if user in YONETICILER else "Tedarikçi"
            log_ekle(user, "Sisteme giriş yaptı")
            st.rerun()
        else:
            st.error("Hatalı şifre!")
else:
    mevcut_user = st.session_state['kullanici']
    
    # --- Yan Menü (Sidebar) ---
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/tr/f/ff/Fenerbah%C3%A7e_SK.png", width=100)
    st.sidebar.title(f"Hoş geldin,\n{mevcut_user}")
    
    # Yenileme Butonu
    if st.sidebar.button("🔄 Verileri Yenile"):
        st.rerun()
        
    secim = st.sidebar.radio("Menü Seçenekleri", ["Sipariş Takip / Operasyon", "Yeni Kayıt & İçeri Aktar", "İşlem Geçmişi (Log)", "Dışarı Aktar (Excel)"])

    # --- 1. SİPARİŞ TAKİP (TABLO GÖRÜNÜMÜ) ---
    if secim == "Sipariş Takip / Operasyon":
        st.header("Sipariş Takip ve Operasyon Paneli")
        
        # Veritabanından verileri çek
        query = "SELECT id as 'ID', sicil_no as 'Sicil No', uye_adi as 'Ad Soyad', urunler as 'Ürünler', durum as 'Durum', kargo_no as 'Kargo No', tarih as 'Kayıt Tarihi' FROM siparisler ORDER BY id DESC"
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            # Tabloyu göster (Sicil, İsim ve Ürünler yan yana)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # Güncelleme Formu
            st.subheader("📦 Durum Güncelle")
            with st.expander("Sipariş Durumunu veya Kargo Numarasını Değiştir"):
                c1, c2, c3 = st.columns([1, 2, 2])
                secilen_id = c1.selectbox("ID Seçin", df['ID'].tolist())
                yeni_statü = c2.selectbox("Yeni Durum", [
                    "Sipariş Alındı", 
                    "Tedarik: Rozet (Engin B.)", 
                    "Tedarik: Plaket (Mevlüt B.)", 
                    "İpek Kutu'ya Sevk Edildi", 
                    "Kargoda", 
                    "Tamamlandı",
                    "Kulüpten Teslim"
                ])
                kargo_input = c3.text_input("Kargo Takip No (Kargodaysa)")
                
                if st.button("Değişiklikleri Kaydet"):
                    c.execute("UPDATE siparisler SET durum = ?, kargo_no = ? WHERE id = ?", (yeni_statü, kargo_input, secilen_id))
                    conn.commit()
                    log_ekle(mevcut_user, f"ID:{secilen_id} nolu siparişi '{yeni_statü}' olarak güncelledi.")
                    st.success(f"ID:{secilen_id} başarıyla güncellendi!")
                    st.rerun()
        else:
            st.info("Henüz sistemde kayıtlı sipariş yok.")

    # --- 2. YENİ KAYIT & İÇERİ AKTAR ---
    elif secim == "Yeni Kayıt & İçeri Aktar":
        t1, t2 = st.tabs(["✍️ Tek Tek Ekle", "📂 Excel/CSV ile Toplu Yükle"])
        
        with t1:
            with st.form("tekil_ekle"):
                f_ad = st.text_input("Üye Adı Soyadı")
                f_sicil = st.text_input("Sicil Numarası")
                f_urun = st.multiselect("Sipariş Edilen Ürünler", [
                    "Üyelik Kiti", "Üyelik Kartı", "Üyelik Sertifikası", 
                    "Üyelik Rozeti", "Üyelik Tişörtü", "Kutu ve Cam Kristal Plaket"
                ])
                f_not = st.text_area("Notlar")
                if st.form_submit_button("Siparişi Kaydet"):
                    if f_ad and f_sicil:
                        tarih_bugun = datetime.now().strftime("%d/%m/%Y")
                        urun_listesi = ", ".join(f_urun)
                        c.execute("INSERT INTO siparisler (uye_adi, sicil_no, urunler, durum, tarih, notlar) VALUES (?,?,?,?,?,?)",
                                  (f_ad, f_sicil, urun_listesi, "Sipariş Alındı", tarih_bugun, f_not))
                        conn.commit()
                        log_ekle(mevcut_user, f"Yeni sipariş oluşturdu: {f_ad}")
                        st.success("Sipariş başarıyla eklendi!")
                    else:
                        st.error("Ad ve Sicil No boş bırakılamaz.")

        with t2:
            st.markdown("### Toplu Yükleme")
            st.write("Dosyanızda şu başlıklar olmalı: **sicil_no**, **uye_adi**, **urunler**")
            up_file = st.file_uploader("Dosya Seç (XLSX veya CSV)", type=['xlsx', 'csv'])
            if up_file:
                try:
                    if up_file.name.endswith('.csv'):
                        df_up = pd.read_csv(up_file, encoding='utf-8-sig')
                    else:
                        df_up = pd.read_excel(up_file)
                    
                    st.write("Yüklenecek Veri Önizlemesi:")
                    st.dataframe(df_up.head())
                    
                    if st.button("Verileri Sisteme Aktar"):
                        for _, r in df_up.iterrows():
                            tarih_up = datetime.now().strftime("%d/%m/%Y")
                            c.execute("INSERT INTO siparisler (uye_adi, sicil_no, urunler, durum, tarih) VALUES (?,?,?,?,?)",
                                      (str(r['uye_adi']), str(r['sicil_no']), str(r['urunler']), "Sipariş Alındı", tarih_up))
                        conn.commit()
                        log_ekle(mevcut_user, "Excel/CSV ile toplu sipariş yükledi.")
                        st.success(f"{len(df_up)} adet sipariş başarıyla aktarıldı!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")

    # --- 3. İŞLEM GEÇMİŞİ ---
    elif secim == "İşlem Geçmişi (Log)":
        st.header("Sistem Hareketleri (Log Kayıtları)")
        log_data = pd.read_sql_query("SELECT zaman as 'Tarih/Saat', kullanici as 'Kullanıcı', islem as 'Yapılan İşlem' FROM islem_gecmisi ORDER BY id DESC", conn)
        st.table(log_data)

    # --- 4. DIŞARI AKTAR ---
    elif secim == "Dışarı Aktar (Excel)":
        st.header("Veritabanı Yedekle / Excel Al")
        full_df = pd.read_sql_query("SELECT * FROM siparisler", conn)
        csv_data = full_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Tüm Veriyi Excel (CSV) Olarak İndir", csv_data, "fb_lojistik_yedek.csv", "text/csv")

    # Çıkış
    if st.sidebar.button("Güvenli Çıkış"):
        del st.session_state['kullanici']
        st.rerun()
