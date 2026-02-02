import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io
import plotly.express as px

# --- VERİTABANI BAĞLANTISI ---
conn = sqlite3.connect('fb_operasyon_merkezi_v2.db', check_same_thread=False)
c = conn.cursor()

# Tablo Yapısı
c.execute('''CREATE TABLE IF NOT EXISTS siparisler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sicil_no TEXT, uye_adi TEXT, telefon_no TEXT, urunler TEXT, adet INTEGER DEFAULT 1,
    durum TEXT, kargo_no TEXT, kargo_tarihi TEXT, tarih TEXT,
    birim_maliyet REAL DEFAULT 0.0, odeme_durumu TEXT DEFAULT 'Bekliyor')''')

# Eksik sütunları ekleme (Yama)
try:
    c.execute("ALTER TABLE siparisler ADD COLUMN telefon_no TEXT")
    c.execute("ALTER TABLE siparisler ADD COLUMN birim_maliyet REAL DEFAULT 0.0")
    conn.commit()
except:
    pass

c.execute('''CREATE TABLE IF NOT EXISTS islem_gecmisi (
    id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici TEXT, islem TEXT, zaman TEXT)''')
conn.commit()

# --- YETKİ VE DURUMLAR (REVİZE EDİLDİ) ---
KULLANICILAR = {
    "Cüneyt Orhan Varol": "fb01", "Mehmet Erkin Ataş": "fb02", 
    "Ersen Avcı": "fb03", "Simay Önder": "fb04",
    "Pervin Hanım": "ipek123", "Mevlüt Bey": "ikba456", "Engin Bey": "kuker789"
}
YONETICILER = ["Cüneyt Orhan Varol", "Mehmet Erkin Ataş", "Ersen Avcı", "Simay Önder"]

# İSTEDİĞİNİZ YENİ DURUM LİSTESİ
DURUMLAR = [
    "Hazırlanıyor (Üye İlişkileri)",
    "Hazırlanıyor (Kuker)",
    "Hazırlanıyor (İkba Kristal)",
    "Hazırlanıyor (İpek Kutu)",
    "Kargoya verildi",
    "Teslim edildi"
]

# Finansal Raporlama için Tedarikçi Eşleşmesi
TEDARIKCI_MAP = {
    "Hazırlanıyor (Kuker)": "Engin Bey (Kuker)",
    "Hazırlanıyor (İkba Kristal)": "Mevlüt Bey (İkba)",
    "Hazırlanıyor (İpek Kutu)": "Pervin Hanım (İpek)",
    "Hazırlanıyor (Üye İlişkileri)": "Kulüp İç Operasyon"
}

def log_ekle(kullanici, islem):
    zaman = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    c.execute("INSERT INTO islem_gecmisi (kullanici, islem, zaman) VALUES (?,?,?)", (kullanici, islem, zaman))
    conn.commit()

# --- ARAYÜZ ---
st.set_page_config(page_title="FB Operasyon v5.6", layout="wide")

if 'kullanici' not in st.session_state:
    st.title("🛡️ FB Operasyon Merkezi")
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
    st.sidebar.title(f"👤 {mevcut_user}")
    secim = st.sidebar.radio("Menü", ["📦 Operasyon & Akış", "💰 Finansal Analiz", "📂 Yeni Kayıt / Aktar", "🗑️ Kayıt Silme", "🕒 İşlem Geçmişi"])

    # --- 1. OPERASYON VE AKIŞ ---
    if secim == "📦 Operasyon & Akış":
        st.header("🚀 Lojistik İş Akış Takibi")
        
        with st.expander("🔍 Gelişmiş Filtreleme & Toplu Arama", expanded=True):
            f1, f2 = st.columns([1, 2])
            with f1:
                s_name = st.text_input("İsim ile Ara")
                s_status = st.selectbox("Durum Seçin", ["Tümü"] + DURUMLAR)
            with f2:
                s_bulk = st.text_area("Toplu Sicil veya Telefon No (Alt alta veya virgülle yapıştırın)")

        # SQL Sorgu
        query = "SELECT * FROM siparisler WHERE 1=1"
        params = []
        
        if s_name:
            query += " AND uye_adi LIKE ?"; params.append(f"%{s_name}%")
        if s_status != "Tümü":
            query += " AND durum = ?"; params.append(s_status)
        if s_bulk:
            liste = [i.strip() for i in s_bulk.replace('\n', ',').split(',') if i.strip()]
            if liste:
                query += f" AND (sicil_no IN ({','.join(['?']*len(liste))}) OR telefon_no IN ({','.join(['?']*len(liste))}))"
                params.extend(liste * 2)
        
        df = pd.read_sql_query(query + " ORDER BY id DESC", conn, params=params)

        if not df.empty:
            st.subheader(f"📋 Sipariş Listesi ({len(df)})")
            
            # Kargo Linki
            df['Kargo Takip'] = df['kargo_no'].apply(lambda x: f"https://kargotakip.yurticikargo.com/query?no={x}" if x else "")

            st.dataframe(df, column_config={
                "Kargo Takip": st.column_config.LinkColumn("📦 Sorgula"),
                "durum": "📌 Statü",
                "birim_maliyet": st.column_config.NumberColumn("Birim Fiyat", format="%.2f ₺"),
                "telefon_no": "📞 Telefon"
            }, use_container_width=True, hide_index=True)

            # Toplu Güncelleme Formu
            with st.form("toplu_guncelle"):
                st.subheader("🛠️ Seçili Kayıtları Yönet")
                df['etiket'] = df['sicil_no'].astype(str) + " - " + df['uye_adi'] + " (ID: " + df['id'].astype(str) + ")"
                label_id_map = dict(zip(df['etiket'], df['id']))
                sel = st.multiselect("Değişiklik yapılacak üyeleri seçin", df['etiket'].tolist())
                
                c1, c2, c3 = st.columns(3)
                n_durum = c1.selectbox("Yeni Durum Belirle", DURUMLAR)
                n_kargo = c2.text_input("Kargo Numarası")
                n_maliyet = c3.number_input("Birim Maliyet (TL)", 0.0)
                
                if st.form_submit_button("Seçilenleri Güncelle"):
                    if sel:
                        ids = [label_id_map[e] for e in sel]
                        for s_id in ids:
                            c.execute("UPDATE siparisler SET durum=?, kargo_no=?, birim_maliyet=? WHERE id=?", (n_durum, n_kargo, n_maliyet, s_id))
                        conn.commit()
                        st.toast(f"{len(ids)} Kayıt Güncellendi!", icon="✅")
                        st.rerun()

    # --- 2. FİNANSAL ANALİZ ---
    elif secim == "💰 Finansal Analiz":
        st.header("💰 Tedarikçi Hakediş Takibi")
        if st.session_state['yetki'] == "Yönetici":
            df_fin = pd.read_sql_query("SELECT * FROM siparisler", conn)
            if not df_fin.empty:
                df_fin['Tedarikçi'] = df_fin['durum'].map(TEDARIKCI_MAP).fillna("Dış Süreç/Teslimat")
                df_fin['Toplam'] = pd.to_numeric(df_fin['adet'], errors='coerce').fillna(1) * pd.to_numeric(df_fin['birim_maliyet'], errors='coerce').fillna(0)
                
                ozet = df_fin.groupby('Tedarikçi')['Toplam'].sum().reset_index()
                st.subheader("📊 Toplam Borç / Hakediş Tablosu")
                st.dataframe(ozet, use_container_width=True)
                
                fig = px.bar(ozet, x='Tedarikçi', y='Toplam', color='Tedarikçi', text_auto='.2s', title="Tedarikçi Ödeme Dağılımı")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Veri bulunamadı.")
        else:
            st.warning("Bu sayfa sadece yöneticilere açıktır.")

    # --- 3. YENİ KAYIT ---
    elif secim == "📂 Yeni Kayıt / Aktar":
        t1, t2 = st.tabs(["✍️ Tek Tek Ekle", "📂 Excel'den Toplu Aktar"])
        with t1:
            with st.form("manuel"):
                col1, col2 = st.columns(2)
                s = col1.text_input("Sicil No")
                a = col2.text_input("Ad Soyad")
                tel = col1.text_input("Telefon No")
                m = col2.number_input("Birim Maliyet (Opsiyonel)", 0.0)
                u = st.text_area("Ürün Detayları")
                if st.form_submit_button("Sisteme Kaydet"):
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, telefon_no, urunler, durum, tarih, birim_maliyet) VALUES (?,?,?,?,?,?,?)", 
                              (s, a, tel, u, "Hazırlanıyor (Üye İlişkileri)", datetime.now().strftime("%d/%m/%Y"), m))
                    conn.commit(); st.success("Kayıt Başarıyla Oluşturuldu!"); st.rerun()
        with t2:
            st.markdown("### 📥 Excel Formatı: `sicil_no, uye_adi, telefon_no, urunler, adet` olmalıdır.")
            up = st.file_uploader("Dosya Seçin", type=['xlsx'])
            if up and st.button("Aktarımı Başlat"):
                df_up = pd.read_excel(up)
                for _, r in df_up.iterrows():
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, telefon_no, urunler, durum, tarih) VALUES (?,?,?,?,?,?)", 
                              (str(r.get('sicil_no','')), str(r.get('uye_adi','')), str(r.get('telefon_no','')), str(r.get('urunler','')), "Hazırlanıyor (Üye İlişkileri)", datetime.now().strftime("%d/%m/%Y")))
                conn.commit(); st.toast("Excel Aktarımı Tamamlandı!", icon="📂"); st.rerun()

    # --- 4. SİLME ---
    elif secim == "🗑️ Kayıt Silme":
        st.header("🗑️ Kayıt Yönetimi (Silme)")
        if st.session_state['yetki'] == "Yönetici":
            df_sil = pd.read_sql_query("SELECT id, sicil_no, uye_adi, durum FROM siparisler", conn)
            if not df_sil.empty:
                df_sil['etiket'] = df_sil['id'].astype(str) + " - " + df_sil['uye_adi']
                id_map_sil = dict(zip(df_sil['etiket'], df_sil['id']))
                sec = st.multiselect("Silinecek Kayıtları Seçin", df_sil['etiket'].tolist())
                if st.button("❌ Seçilenleri Kalıcı Olarak Sil"):
                    if sec:
                        for s in sec: c.execute("DELETE FROM siparisler WHERE id=?", (id_map_sil[s],))
                        conn.commit(); log_ekle(mevcut_user, f"{len(sec)} kayıt sildi."); st.rerun()
                
                st.divider()
                if st.checkbox("⚠️ TÜM VERİLERİ SIFIRLA"):
                    if st.button("🔥 VERİTABANINI TEMİZLE"):
                        c.execute("DELETE FROM siparisler"); conn.commit(); log_ekle(mevcut_user, "Tüm verileri temizledi."); st.rerun()
        else:
            st.warning("Bu alan yetki gerektirir.")

    # --- 5. LOG ---
    elif secim == "🕒 İşlem Geçmişi":
        st.dataframe(pd.read_sql_query("SELECT * FROM islem_gecmisi ORDER BY id DESC LIMIT 500", conn), use_container_width=True)

    if st.sidebar.button("🚪 Güvenli Çıkış"):
        del st.session_state['kullanici']; st.rerun()
