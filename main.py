import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io
import plotly.express as px

# --- VERİTABANI BAĞLANTISI ---
conn = sqlite3.connect('fb_operasyon_merkezi_v2.db', check_same_thread=False)
c = conn.cursor()

# Tabloyu başlat
c.execute('''CREATE TABLE IF NOT EXISTS siparisler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sicil_no TEXT, uye_adi TEXT, urunler TEXT, adet INTEGER DEFAULT 1,
    durum TEXT, kargo_no TEXT, kargo_tarihi TEXT, tarih TEXT,
    birim_maliyet REAL DEFAULT 0.0, odeme_durumu TEXT DEFAULT 'Bekliyor')''')

# --- KRİTİK HATA DÜZELTME: Sütun Kontrolü ---
# Eğer veritabanı eskiyse ve sütunlar yoksa burası otomatik ekler
try:
    c.execute("ALTER TABLE siparisler ADD COLUMN birim_maliyet REAL DEFAULT 0.0")
    c.execute("ALTER TABLE siparisler ADD COLUMN odeme_durumu TEXT DEFAULT 'Bekliyor'")
    conn.commit()
except:
    # Sütunlar zaten varsa hata verir, burayı sessizce geçiyoruz
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

TEDARIKCI_MAP = {
    "Kuker hazırlıyor": "Engin Bey",
    "İKBA Kristal hazırlıyor": "Mevlüt Bey",
    "İpek Kutu'ya gönderildi": "Pervin Hanım"
}

def log_ekle(kullanici, islem):
    zaman = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    c.execute("INSERT INTO islem_gecmisi (kullanici, islem, zaman) VALUES (?,?,?)", (kullanici, islem, zaman))
    conn.commit()

# --- ARAYÜZ ---
st.set_page_config(page_title="FB Operasyon v5.1", layout="wide")

if 'kullanici' not in st.session_state:
    st.title("🛡️ FB Operasyon Merkezi v5.1")
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
        df_all = pd.read_sql_query("SELECT * FROM siparisler", conn)
        
        if not df_all.empty:
            m1, m2, m3 = st.columns([1, 1, 2])
            m1.metric("📌 Toplam Kayıt", len(df_all))
            m2.metric("✅ Tamamlanan", len(df_all[df_all['durum'] == "Tamamlandı"]))
            fig = px.pie(df_all, names='durum', hole=.4, height=200)
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            m3.plotly_chart(fig, use_container_width=True)

        st.divider()

        # Filtreler
        f1, f2 = st.columns(2)
        s_name = f1.text_input("İsim ile Ara")
        s_status = f2.selectbox("Durum", ["Tümü"] + DURUMLAR)
        
        query = "SELECT * FROM siparisler WHERE 1=1"
        params = []
        if s_name: query += " AND uye_adi LIKE ?"; params.append(f"%{s_name}%")
        if s_status != "Tümü": query += " AND durum = ?"; params.append(s_status)
        
        df = pd.read_sql_query(query, conn, params=params)

        if not df.empty:
            df['Kargo Takip'] = df['kargo_no'].apply(lambda x: f"https://kargotakip.yurticikargo.com/query?no={x}" if x else "")
            
            st.dataframe(df, column_config={
                "Kargo Takip": st.column_config.LinkColumn("📦 Kargo Sorgula"),
                "birim_maliyet": st.column_config.NumberColumn("Fiyat (TL)", format="%.2f ₺"),
                "tarih": "📅 Kayıt"
            }, use_container_width=True, hide_index=True)

            with st.form("guncelle_form"):
                st.subheader("🛠️ Statü Güncelle")
                df['etiket'] = df['id'].astype(str) + " | " + df['uye_adi']
                id_map = dict(zip(df['etiket'], df['id']))
                sel = st.multiselect("Üyeleri Seç", df['etiket'].tolist())
                c1, c2, c3 = st.columns(3)
                n_durum = c1.selectbox("Yeni Statü", DURUMLAR)
                n_kargo = c2.text_input("Kargo No")
                n_maliyet = c3.number_input("Birim Maliyet (TL)", 0.0)
                
                if st.form_submit_button("Güncellemeyi Uygula"):
                    if sel:
                        for e in sel:
                            s_id = id_map[e]
                            c.execute("UPDATE siparisler SET durum=?, kargo_no=?, birim_maliyet=? WHERE id=?", 
                                     (n_durum, n_kargo, n_maliyet, s_id))
                        conn.commit()
                        log_ekle(mevcut_user, f"{len(sel)} kayıt güncellendi.")
                        st.success("Başarılı!")
                        st.rerun()

    # --- 2. FİNANSAL ANALİZ ---
    elif secim == "💰 Finansal Analiz":
        st.header("💰 Tedarikçi Hakediş ve Maliyet")
        if st.session_state['yetki'] == "Yönetici":
            df_fin = pd.read_sql_query("SELECT * FROM siparisler", conn)
            if not df_fin.empty:
                df_fin['Tedarikçi'] = df_fin['durum'].map(TEDARIKCI_MAP).fillna("Diğer/Kulüp")
                # Hata önleyici: Eğer adet veya maliyet boşsa 0 kabul et
                df_fin['adet'] = pd.to_numeric(df_fin['adet'], errors='coerce').fillna(1)
                df_fin['birim_maliyet'] = pd.to_numeric(df_fin['birim_maliyet'], errors='coerce').fillna(0)
                
                df_fin['Toplam'] = df_fin['adet'] * df_fin['birim_maliyet']
                
                ozet = df_fin.groupby('Tedarikçi')['Toplam'].sum().reset_index()
                st.subheader("📊 Tedarikçi Bazlı Toplam Borçlanma")
                st.dataframe(ozet, use_container_width=True)
                
                fig_fin = px.bar(ozet, x='Tedarikçi', y='Toplam', color='Tedarikçi', title="Ödeme Dağılımı (₺)")
                st.plotly_chart(fig_fin, use_container_width=True)
            else:
                st.info("Veri bulunamadı.")
        else:
            st.warning("Bu alanı görmeye yetkiniz yok.")

    # ... (Diğer menüler: Yeni Kayıt, Kayıt Silme, Log aynı kalıyor)
    elif secim == "📂 Yeni Kayıt / Aktar":
        t1, t2 = st.tabs(["✍️ Tekil", "📂 Excel"])
        with t1:
            with st.form("tek_ekle"):
                s = st.text_input("Sicil No"); a = st.text_input("Ad Soyad"); u = st.text_area("Ürünler")
                m = st.number_input("Birim Maliyet", 0.0)
                if st.form_submit_button("Kaydet"):
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, urunler, durum, tarih, birim_maliyet) VALUES (?,?,?,?,?,?)",
                              (s, a, u, "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y"), m))
                    conn.commit(); st.success("Eklendi!"); st.rerun()
        with t2:
            up = st.file_uploader("Excel Yükle", type=['xlsx'])
            if up and st.button("Aktar"):
                df_up = pd.read_excel(up)
                for _, r in df_up.iterrows():
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, urunler, durum, tarih, birim_maliyet) VALUES (?,?,?,?,?,?)",
                              (str(r.get('sicil_no','')), str(r.get('uye_adi','')), str(r.get('urunler','')), "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y"), 0.0))
                conn.commit(); st.success("Aktarıldı!"); st.rerun()

    elif secim == "🗑️ Kayıt Silme":
        st.header("🗑️ Kayıt Silme Paneli")
        if st.session_state['yetki'] == "Yönetici":
            df_sil = pd.read_sql_query("SELECT id, sicil_no, uye_adi FROM siparisler", conn)
            if not df_sil.empty:
                df_sil['etiket'] = df_sil['id'].astype(str) + " - " + df_sil['uye_adi']
                id_sil_map = dict(zip(df_sil['etiket'], df_sil['id']))
                silinecekler = st.multiselect("Silinecek Kayıtları Seçin", df_sil['etiket'].tolist())
                
                if st.button("❌ Seçilenleri Kalıcı Olarak Sil"):
                    if silinecekler:
                        for s in silinecekler:
                            c.execute("DELETE FROM siparisler WHERE id=?", (id_sil_map[s],))
                        conn.commit()
                        log_ekle(mevcut_user, f"{len(silinecekler)} kayıt sildi.")
                        st.error("Kayıtlar Silindi!")
                        st.rerun()
                
                st.divider()
                if st.checkbox("🔥 Tüm Veritabanını Temizle"):
                    if st.button("HER ŞEYİ SİL"):
                        c.execute("DELETE FROM siparisler")
                        conn.commit()
                        log_ekle(mevcut_user, "Tüm veritabanı sıfırlandı!")
                        st.rerun()
            else:
                st.info("Silinecek veri yok.")
        else:
            st.warning("Bu yetki sadece yöneticilerdedir.")

    elif secim == "🕒 İşlem Geçmişi":
        st.dataframe(pd.read_sql_query("SELECT * FROM islem_gecmisi ORDER BY id DESC", conn), use_container_width=True)

    if st.sidebar.button("🚪 Çıkış"):
        del st.session_state['kullanici']; st.rerun()
