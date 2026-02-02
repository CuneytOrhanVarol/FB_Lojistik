import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io
import plotly.express as px  # Görselleştirme için eklendi

# --- VERİTABANI BAĞLANTISI ---
conn = sqlite3.connect('fb_operasyon_merkezi_v2.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS siparisler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sicil_no TEXT, uye_adi TEXT, urunler TEXT, adet INTEGER DEFAULT 1,
    durum TEXT, kargo_no TEXT, kargo_tarihi TEXT, tarih TEXT,
    maliyet REAL DEFAULT 0.0)''') # Finansal hazırlık için maliyet sütunu eklendi

c.execute('''CREATE TABLE IF NOT EXISTS islem_gecmisi (
    id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici TEXT, islem TEXT, zaman TEXT)''')
conn.commit()

# --- YETKİ VE DURUMLAR ---
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

def bekleme_suresi_hesapla(kayit_tarihi):
    try:
        t1 = datetime.strptime(kayit_tarihi, "%d/%m/%Y")
        t2 = datetime.now()
        return (t2 - t1).days
    except:
        return 0

# --- ARAYÜZ ---
st.set_page_config(page_title="FB Operasyon Merkezi v4", layout="wide")

if 'kullanici' not in st.session_state:
    st.title("🛡️ FB Operasyon Merkezi v4")
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
    secim = st.sidebar.radio("Menü", ["📦 Operasyon & Akış", "📂 Yeni Kayıt / Aktar", "🕒 İşlem Geçmişi", "📊 Veri Yönetimi"])

    if secim == "📦 Operasyon & Akış":
        st.header("🚀 Lojistik İş Akış Takibi")
        
        # --- DASHBOARD (Görsel İstatistikler) ---
        stats_query = "SELECT durum, COUNT(*) as sayi FROM siparisler GROUP BY durum"
        df_stats = pd.read_sql_query(stats_query, conn)
        
        if not df_stats.empty:
            m1, m2 = st.columns([1, 2])
            with m1:
                st.metric("📌 Toplam Kayıt", df_stats['sayi'].sum())
                hazir = df_stats[df_stats['durum'] == "Hazırlanıyor"]['sayi'].sum()
                st.metric("⏳ Bekleyen Hazırlanıyor", hazir)
            with m2:
                fig = px.pie(df_stats, values='sayi', names='durum', hole=.4, 
                             color_discrete_sequence=px.colors.qualitative.Set3)
                fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=180, showlegend=True)
                st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # --- FİLTRELEME ---
        with st.expander("🔍 Arama Seçenekleri", expanded=False):
            f1, f2, f3 = st.columns([1, 1, 2])
            with f1: s_name = st.text_input("İsim ile Ara")
            with f2: s_status = st.selectbox("Durum", ["Tümü"] + DURUMLAR)
            with f3: s_bulk = st.text_area("Toplu Sicil Sorgula")

        query = "SELECT * FROM siparisler WHERE 1=1"
        params = []
        if s_name: query += " AND uye_adi LIKE ?"; params.append(f"%{s_name}%")
        if s_status != "Tümü": query += " AND durum = ?"; params.append(s_status)
        if s_bulk:
            siciller = [s.strip() for s in s_bulk.replace('\n', ',').split(',') if s.strip()]
            if siciller:
                query += f" AND sicil_no IN ({','.join(['?']*len(siciller))})"
                params.extend(siciller)
        
        df = pd.read_sql_query(query, conn, params=params)

        if not df.empty:
            df['Bekleme (Gün)'] = df['tarih'].apply(bekleme_suresi_hesapla)
            
            # --- TIKLANABİLİR TABLO ---
            st.subheader(f"📋 Sipariş Listesi ({len(df)} Kayıt)")
            
            # Kargo Linki Oluşturma (Örnek: Yurtiçi Kargo sorgu linki şablonu)
            df['Kargo Takip'] = df['kargo_no'].apply(lambda x: f"https://kargotakip.yurticikargo.com/query?no={x}" if x else "")

            st.dataframe(
                df,
                column_config={
                    "Kargo Takip": st.column_config.LinkColumn("📦 Kargo Sorgula"),
                    "Bekleme (Gün)": st.column_config.ProgressColumn("⏳ Süreç Gecikmesi", min_value=0, max_value=15, format="%d Gün"),
                    "durum": "📌 Statü",
                    "tarih": "📅 Kayıt Tarihi"
                },
                use_container_width=True, hide_index=True
            )

            # --- GÜNCELLEME FORMU ---
            with st.form("islem_formu"):
                st.subheader("🛠️ Toplu İşlem Paneli")
                df['etiket'] = df['sicil_no'].astype(str) + " - " + df['uye_adi'] + " (ID: " + df['id'].astype(str) + ")"
                etiket_to_id = dict(zip(df['etiket'], df['id']))
                
                col1, col2 = st.columns(2)
                secilenler = col1.multiselect("Kayıtları Seçin", df['etiket'].tolist())
                yeni_d = col2.selectbox("Yeni Statü", DURUMLAR)
                
                col3, col4 = st.columns(2)
                k_no = col3.text_input("Kargo Takip No")
                k_tar = col4.date_input("İşlem Tarihi", datetime.now()).strftime("%d/%m/%Y")
                
                if st.form_submit_button("Seçilenleri Güncelle"):
                    if secilenler:
                        ids = [etiket_to_id[e] for e in secilenler]
                        for s_id in ids:
                            c.execute("UPDATE siparisler SET durum=?, kargo_no=?, kargo_tarihi=? WHERE id=?", (yeni_d, k_no, k_tar, s_id))
                        conn.commit()
                        log_ekle(mevcut_user, f"{len(ids)} kayıt güncellendi: {yeni_d}")
                        st.toast(f"{len(ids)} Kayıt Güncellendi!", icon="✅")
                        st.rerun()

    elif secim == "📂 Yeni Kayıt / Aktar":
        t1, t2 = st.tabs(["✍️ Tekil Kayıt", "📂 Excel'den Aktar"])
        with t1:
            with st.form("yeni"):
                s = st.text_input("Sicil No"); a = st.text_input("Ad Soyad"); u = st.text_area("Ürünler")
                if st.form_submit_button("Kaydet"):
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, urunler, durum, tarih) VALUES (?,?,?,?,?)",
                              (s, a, u, "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y")))
                    conn.commit(); st.success("Kaydedildi!"); st.rerun()
        with t2:
            st.markdown("### 📥 Excel Yükleme Rehberi")
            # Şablon İndirme Butonu
            template_df = pd.DataFrame(columns=["sicil_no", "uye_adi", "urunler", "adet"])
            tmp_download = io.BytesIO()
            with pd.ExcelWriter(tmp_download, engine='openpyxl') as writer:
                template_df.to_excel(writer, index=False)
            st.download_button("📥 Örnek Şablonu İndir", tmp_download.getvalue(), "fb_lojistik_sablon.xlsx")
            
            up = st.file_uploader("Doldurduğunuz Excel'i Seçin", type=['xlsx'])
            if up and st.button("Aktarımı Başlat"):
                df_up = pd.read_excel(up)
                for _, r in df_up.iterrows():
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, urunler, durum, tarih) VALUES (?,?,?,?,?)",
                              (str(r.get('sicil_no','')), str(r.get('uye_adi','')), str(r.get('urunler','')), "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y")))
                conn.commit(); st.toast("Excel Başarıyla Aktarıldı!", icon="📂"); st.rerun()

    elif secim == "📊 Veri Yönetimi":
        st.subheader("📥 Veri Yedekleme ve Raporlama")
        if st.button("Tüm Veritabanını Excel Olarak Hazırla"):
            df_out = pd.read_sql_query("SELECT * FROM siparisler", conn)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_out.to_excel(writer, index=False)
            st.download_button("💾 Excel Dosyasını İndir", output.getvalue(), "fb_lojistik_tam_yedek.xlsx")

    elif secim == "🕒 İşlem Geçmişi":
        st.subheader("🕵️ Sistem Hareketleri")
        st.dataframe(pd.read_sql_query("SELECT * FROM islem_gecmisi ORDER BY id DESC LIMIT 500", conn), use_container_width=True)

    if st.sidebar.button("🚪 Güvenli Çıkış"):
        del st.session_state['kullanici']; st.rerun()
