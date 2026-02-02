import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io
import plotly.express as px

# --- VERİTABANI BAĞLANTISI ---
conn = sqlite3.connect('fb_operasyon_merkezi_v2.db', check_same_thread=False)
c = conn.cursor()

# Tablo Yapısı ve Yama
c.execute('''CREATE TABLE IF NOT EXISTS siparisler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sicil_no TEXT, uye_adi TEXT, telefon_no TEXT, urunler TEXT, adet INTEGER DEFAULT 1,
    durum TEXT, kargo_no TEXT, kargo_tarihi TEXT, tarih TEXT,
    birim_maliyet REAL DEFAULT 0.0, odeme_durumu TEXT DEFAULT 'Bekliyor')''')

try:
    c.execute("ALTER TABLE siparisler ADD COLUMN tarih TEXT")
    conn.commit()
except:
    pass

# --- AYARLAR ---
KULLANICILAR = {"Cüneyt Orhan Varol": "fb01", "Mehmet Erkin Ataş": "fb02", "Ersen Avcı": "fb03", "Simay Önder": "fb04", "Pervin Hanım": "ipek123", "Mevlüt Bey": "ikba456", "Engin Bey": "kuker789"}
YONETICILER = ["Cüneyt Orhan Varol", "Mehmet Erkin Ataş", "Ersen Avcı", "Simay Önder"]
DURUMLAR = ["Hazırlanıyor (Üye İlişkileri)", "Hazırlanıyor (Kuker)", "Hazırlanıyor (İkba Kristal)", "Hazırlanıyor (İpek Kutu)", "Kargoya verildi", "Teslim edildi"]

def log_ekle(kullanici, islem):
    zaman = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    c.execute("INSERT INTO islem_gecmisi (kullanici, islem, zaman) VALUES (?,?,?)", (kullanici, islem, zaman))
    conn.commit()

st.set_page_config(page_title="FB Operasyon v6.0", layout="wide")

if 'kullanici' not in st.session_state:
    st.title("🛡️ FB Operasyon Merkezi")
    user = st.selectbox("Kullanıcı Seçin", list(KULLANICILAR.keys()))
    sifre = st.text_input("Şifre", type="password")
    if st.button("Sisteme Giriş Yap"):
        if KULLANICILAR.get(user) == sifre:
            st.session_state['kullanici'] = user
            st.session_state['yetki'] = "Yönetici" if user in YONETICILER else "Tedarikçi"
            st.rerun()
else:
    mevcut_user = st.session_state['kullanici']
    st.sidebar.title(f"👤 {mevcut_user}")
    secim = st.sidebar.radio("Menü", ["📦 Operasyon Paneli", "📈 Performans & Finans", "📂 Kayıt Ekle / Aktar", "🗑️ Yönetim", "🕒 Log"])

    # --- 1. OPERASYON PANELİ (YENİLENMİŞ VE PRATİK) ---
    if secim == "📦 Operasyon Paneli":
        st.header("🚀 Hızlı Operasyon Akışı")
        
        # Üst Metrikler (Tıklanabilir Filtre Hissi)
        df_all = pd.read_sql_query("SELECT * FROM siparisler", conn)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam", len(df_all))
        c2.metric("Üye İlişkilerinde", len(df_all[df_all['durum'] == DURUMLAR[0]]))
        c3.metric("Tedarikçilerde", len(df_all[df_all['durum'].str.contains("Hazırlanıyor") & ~df_all['durum'].contains("Üye")]))
        c4.metric("Kargoda", len(df_all[df_all['durum'] == "Kargoya verildi"]))

        # Hızlı Arama ve Filtre
        with st.container():
            col_a, col_b = st.columns([2, 1])
            s_query = col_a.text_input("🔍 İsim, Sicil veya Telefon ile Hızlı Ara")
            s_status = col_b.selectbox("Durum Filtresi", ["Tümü"] + DURUMLAR)

        query = "SELECT * FROM siparisler WHERE 1=1"
        params = []
        if s_query:
            query += " AND (uye_adi LIKE ? OR sicil_no LIKE ? OR telefon_no LIKE ?)"
            params.extend([f"%{s_query}%"]*3)
        if s_status != "Tümü":
            query += " AND durum = ?"; params.append(s_status)
        
        df = pd.read_sql_query(query + " ORDER BY id DESC", conn, params=params)

        # PRATİK TABLO VE SEÇİM
        if not df.empty:
            st.write("### İşlem Bekleyen Kayıtlar")
            # Bekleme süresi hesapla (Görsel Yardımcı)
            df['Gün'] = df['tarih'].apply(lambda x: (datetime.now() - datetime.strptime(x, "%d/%m/%Y")).days if x else 0)
            
            # Tablo Görünümü
            event = st.dataframe(
                df,
                column_config={
                    "Gün": st.column_config.ProgressColumn("Gecikme", min_value=0, max_value=7, format="%d Gün"),
                    "durum": "📌 Statü"
                },
                use_container_width=True,
                on_select="rerun",
                selection_mode="multiple_rows"
            )

            # HIZLI AKSİYON BUTONLARI
            selected_rows = event.selection.rows
            if selected_rows:
                st.info(f"{len(selected_rows)} kayıt seçildi. Hızlı işlem yapın:")
                btn_cols = st.columns(len(DURUMLAR))
                for i, d_adi in enumerate(DURUMLAR):
                    if btn_cols[i].button(d_adi.split("(")[-1].replace(")", ""), key=d_adi):
                        ids = df.iloc[selected_rows]['id'].tolist()
                        for s_id in ids:
                            c.execute("UPDATE siparisler SET durum=? WHERE id=?", (d_adi, s_id))
                        conn.commit()
                        st.success("Güncellendi!")
                        st.rerun()

    # --- 2. PERFORMANS GRAFİKLERİ ---
    elif secim == "📈 Performans & Finans":
        st.header("📈 Operasyonel Performans Analizi")
        df_p = pd.read_sql_query("SELECT * FROM siparisler", conn)
        
        if not df_p.empty:
            p1, p2 = st.columns(2)
            
            # 1. Günlük Kayıt Performansı
            df_p['tarih_dt'] = pd.to_datetime(df_p['tarih'], format="%d/%m/%Y")
            daily_count = df_p.groupby('tarih_dt').size().reset_index(name='Adet')
            fig1 = px.line(daily_count, x='tarih_dt', y='Adet', title="Günlük Kayıt Giriş Hızı", markers=True)
            p1.plotly_chart(fig1, use_container_width=True)
            
            # 2. Durum Dağılımı
            fig2 = px.bar(df_p.groupby('durum').size().reset_index(name='Sayı'), x='durum', y='Sayı', color='durum', title="Yük Dağılımı")
            p2.plotly_chart(fig2, use_container_width=True)

            # 3. Bekleme Süresi Analizi
            st.subheader("⚠️ En Çok Bekleyen Siparişler")
            df_p['Bekleme'] = df_p['tarih'].apply(lambda x: (datetime.now() - datetime.strptime(x, "%d/%m/%Y")).days if x else 0)
            st.dataframe(df_p[df_p['durum'] != "Teslim edildi"].sort_values('Bekleme', ascending=False).head(10), use_container_width=True)
        else:
            st.info("Analiz için yeterli veri yok.")

    # ... (Diğer Kayıt ve Yönetim kısımları v5.6 ile aynı kalabilir)
