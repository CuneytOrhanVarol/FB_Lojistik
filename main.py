import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io
import plotly.express as px

# --- VERİTABANI BAĞLANTISI ---
conn = sqlite3.connect('fb_operasyon_merkezi_v2.db', check_same_thread=False)
c = conn.cursor()

# Tabloyu başlat (Telefon No eklendi)
c.execute('''CREATE TABLE IF NOT EXISTS siparisler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sicil_no TEXT, uye_adi TEXT, telefon_no TEXT, urunler TEXT, adet INTEGER DEFAULT 1,
    durum TEXT, kargo_no TEXT, kargo_tarihi TEXT, tarih TEXT,
    birim_maliyet REAL DEFAULT 0.0, odeme_durumu TEXT DEFAULT 'Bekliyor')''')

# --- Sütun Kontrolü (Hata Önleyici Yama) ---
try:
    c.execute("ALTER TABLE siparisler ADD COLUMN telefon_no TEXT")
    c.execute("ALTER TABLE siparisler ADD COLUMN birim_maliyet REAL DEFAULT 0.0")
    c.execute("ALTER TABLE siparisler ADD COLUMN odeme_durumu TEXT DEFAULT 'Bekliyor'")
    conn.commit()
except:
    pass

c.execute('''CREATE TABLE IF NOT EXISTS islem_gecmisi (
    id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici TEXT, islem TEXT, zaman TEXT)''')
conn.commit()

# --- YETKİ VE AYARLAR ---
KULLANICILAR = {
    "Cüneyt Orhan Varol": "fb01", "Mehmet Erkin Ataş": "fb02", 
    "Ersen Avcı": "fb03", "Simay Önder": "fb04",
    "Pervin Hanım": "ipek123", "Mevlüt Bey": "ikba456", "Engin Bey": "kuker789"
}
YONETICILER = ["Cüneyt Orhan Varol", "Mehmet Erkin Ataş", "Ersen Avcı", "Simay Önder"]
DURUMLAR = ["Hazırlanıyor", "Kuker hazırlıyor", "İKBA Kristal hazırlıyor", "İpek Kutu'ya gönderildi", "Kargoda", "Kulüpten Teslim", "Tamamlandı"]
TEDARIKCI_MAP = {"Kuker hazırlıyor": "Engin Bey", "İKBA Kristal hazırlıyor": "Mevlüt Bey", "İpek Kutu'ya gönderildi": "Pervin Hanım"}

def log_ekle(kullanici, islem):
    zaman = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    c.execute("INSERT INTO islem_gecmisi (kullanici, islem, zaman) VALUES (?,?,?)", (kullanici, islem, zaman))
    conn.commit()

# --- ARAYÜZ ---
st.set_page_config(page_title="FB Operasyon v5.5", layout="wide")

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
        
        # Filtreleme Alanı
        with st.expander("🔍 Gelişmiş / Toplu Arama Paneli", expanded=True):
            f1, f2 = st.columns([1, 2])
            with f1:
                s_name = st.text_input("İsim ile Ara")
                s_status = st.selectbox("Durum Filtrele", ["Tümü"] + DURUMLAR)
            with f2:
                s_bulk = st.text_area("Toplu Sicil No veya Telefon No (Alt alta veya virgülle yapıştırın)")
            s_btn = st.button("Filtrele")

        # SQL Sorgu Oluşturma
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
                params.extend(liste * 2) # Hem sicil hem telefon için aynı listeyi ekliyoruz
        
        df = pd.read_sql_query(query + " ORDER BY id DESC", conn, params=params)

        if not df.empty:
            st.subheader(f"📋 Listelenen Kayıtlar ({len(df)})")
            st.dataframe(df, column_config={
                "kargo_no": "📦 Kargo No",
                "birim_maliyet": st.column_config.NumberColumn("Fiyat", format="%.2f ₺"),
                "telefon_no": "📞 Telefon"
            }, use_container_width=True, hide_index=True)

            with st.form("toplu_guncelle"):
                st.subheader("🛠️ Seçili Kayıtları Güncelle")
                df['etiket'] = df['sicil_no'].astype(str) + " - " + df['uye_adi'] + " (ID: " + df['id'].astype(str) + ")"
                label_id_map = dict(zip(df['etiket'], df['id']))
                sel = st.multiselect("Üyeleri Seçin", df['etiket'].tolist())
                
                c1, c2, c3 = st.columns(3)
                n_durum = c1.selectbox("Yeni Statü", DURUMLAR)
                n_kargo = c2.text_input("Kargo No")
                n_maliyet = c3.number_input("Birim Maliyet (TL)", 0.0)
                
                if st.form_submit_button("Güncelle"):
                    if sel:
                        ids = [label_id_map[e] for e in sel]
                        for s_id in ids:
                            c.execute("UPDATE siparisler SET durum=?, kargo_no=?, birim_maliyet=? WHERE id=?", (n_durum, n_kargo, n_maliyet, s_id))
                        conn.commit()
                        st.success(f"{len(ids)} Kayıt Güncellendi!")
                        st.rerun()

    # --- 2. FİNANSAL ANALİZ ---
    elif secim == "💰 Finansal Analiz":
        st.header("💰 Finansal Takip")
        if st.session_state['yetki'] == "Yönetici":
            df_fin = pd.read_sql_query("SELECT * FROM siparisler", conn)
            if not df_fin.empty:
                df_fin['Tedarikçi'] = df_fin['durum'].map(TEDARIKCI_MAP).fillna("Diğer")
                df_fin['Toplam'] = pd.to_numeric(df_fin['adet'], errors='coerce').fillna(1) * pd.to_numeric(df_fin['birim_maliyet'], errors='coerce').fillna(0)
                ozet = df_fin.groupby('Tedarikçi')['Toplam'].sum().reset_index()
                st.dataframe(ozet, use_container_width=True)
                st.plotly_chart(px.bar(ozet, x='Tedarikçi', y='Toplam', color='Tedarikçi'), use_container_width=True)
        else:
            st.warning("Bu alan yöneticiye özeldir.")

    # --- 3. YENİ KAYIT ---
    elif secim == "📂 Yeni Kayıt / Aktar":
        t1, t2 = st.tabs(["✍️ Tekil", "📂 Excel"])
        with t1:
            with st.form("add"):
                s = st.text_input("Sicil No"); a = st.text_input("Ad Soyad"); tel = st.text_input("Telefon No"); u = st.text_area("Ürünler")
                if st.form_submit_button("Kaydet"):
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, telefon_no, urunler, durum, tarih) VALUES (?,?,?,?,?,?)", (s, a, tel, u, "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y")))
                    conn.commit(); st.success("Kaydedildi!"); st.rerun()
        with t2:
            st.info("Sütunlar: sicil_no, uye_adi, telefon_no, urunler, adet")
            up = st.file_uploader("Excel", type=['xlsx'])
            if up and st.button("Aktar"):
                df_up = pd.read_excel(up)
                for _, r in df_up.iterrows():
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, telefon_no, urunler, durum, tarih) VALUES (?,?,?,?,?,?)", (str(r.get('sicil_no','')), str(r.get('uye_adi','')), str(r.get('telefon_no','')), str(r.get('urunler','')), "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y")))
                conn.commit(); st.success("Aktarıldı!"); st.rerun()

    # --- 4. SİLME ---
    elif secim == "🗑️ Kayıt Silme":
        st.header("🗑️ Kayıt Silme")
        if st.session_state['yetki'] == "Yönetici":
            df_sil = pd.read_sql_query("SELECT id, sicil_no, uye_adi FROM siparisler", conn)
            if not df_sil.empty:
                sel_sil = st.multiselect("Silinecekleri Seç", df_sil['id'].tolist())
                if st.button("Seçilenleri Sil"):
                    for i in sel_sil: c.execute("DELETE FROM siparisler WHERE id=?", (i,))
                    conn.commit(); st.error("Silindi!"); st.rerun()
                if st.checkbox("Her şeyi sil") and st.button("🔥 TÜMÜNÜ SİL"):
                    c.execute("DELETE FROM siparisler"); conn.commit(); st.rerun()
        else: st.warning("Yetkisiz Giriş")

    # --- 5. LOG ---
    elif secim == "🕒 İşlem Geçmişi":
        st.dataframe(pd.read_sql_query("SELECT * FROM islem_gecmisi ORDER BY id DESC", conn), use_container_width=True)

    if st.sidebar.button("🚪 Çıkış"): del st.session_state['kullanici']; st.rerun()
