import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# --- VERİTABANI BAĞLANTISI (KRİTİK: v2 olarak sabitlendi) ---
conn = sqlite3.connect('fb_operasyon_merkezi_v2.db', check_same_thread=False)
c = conn.cursor()

# Tabloları kontrol et (Veri varsa dokunmaz, yoksa oluşturur)
c.execute('''CREATE TABLE IF NOT EXISTS siparisler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sicil_no TEXT, uye_adi TEXT, urunler TEXT, adet INTEGER DEFAULT 1,
    durum TEXT, kargo_no TEXT, kargo_tarihi TEXT, tarih TEXT)''')

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

# --- ARAYÜZ AYARLARI ---
st.set_page_config(page_title="FB Kongre Lojistik v3", layout="wide")

if 'kullanici' not in st.session_state:
    st.title("🛡️ FB Operasyon Merkezi Giriş")
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
    secim = st.sidebar.radio("Menü", ["📦 Operasyon Takip", "📂 Yeni Kayıt / Aktar", "🕒 İşlem Geçmişi", "📊 Veri Yönetimi"])

    if secim == "📦 Operasyon Takip":
        st.header("🚀 Lojistik İş Akışı")
        
        # --- DASHBOARD ---
        df_ozet = pd.read_sql_query("SELECT durum FROM siparisler", conn)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📌 Toplam Kayıt", len(df_ozet))
        c2.metric("⏳ Bekleyen", len(df_ozet[df_ozet['durum'] == "Hazırlanıyor"]))
        c3.metric("🚚 Kargoda", len(df_ozet[df_ozet['durum'] == "Kargoda"]))
        c4.metric("✅ Tamamlanan", len(df_ozet[df_ozet['durum'] == "Tamamlandı"]))

        st.divider()

        # --- ARAMA ---
        with st.expander("🔍 Filtreleme ve Toplu Sicil Arama", expanded=True):
            f1, f2, f3 = st.columns([1, 1, 2])
            with f1: s_name = st.text_input("İsim ile Ara")
            with f2: s_status = st.selectbox("Durum Filtresi", ["Tümü"] + DURUMLAR)
            with f3: s_bulk = st.text_area("Toplu Sicil (Alt alta yapıştırın)")

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
            
            def color_rows(row):
                if row['durum'] == "Tamamlandı": return ['background-color: #d4edda'] * len(row)
                if row['Bekleme (Gün)'] >= 2 and row['durum'] != "Tamamlandı": return ['background-color: #f8d7da'] * len(row)
                return [''] * len(row)

            st.dataframe(df.style.apply(color_rows, axis=1), use_container_width=True, hide_index=True)

            # --- GÜNCELLEME FORMU ---
            with st.form("islem_formu"):
                st.subheader("🛠️ Toplu Durum Güncelleme")
                df['etiket'] = df['sicil_no'].astype(str) + " - " + df['uye_adi'] + " (ID: " + df['id'].astype(str) + ")"
                etiket_to_id = dict(zip(df['etiket'], df['id']))
                
                col1, col2 = st.columns(2)
                secilenler = col1.multiselect("Kayıtları Seçin", df['etiket'].tolist())
                yeni_d = col2.selectbox("Yeni Durum Seçin", DURUMLAR)
                
                col3, col4 = st.columns(2)
                k_no = col3.text_input("Kargo Takip No")
                k_tar = col4.date_input("İşlem Tarihi", datetime.now()).strftime("%d/%m/%Y")
                
                if st.form_submit_button("Seçilenleri Güncelle"):
                    if secilenler:
                        ids = [etiket_to_id[e] for e in secilenler]
                        for s_id in ids:
                            c.execute("UPDATE siparisler SET durum=?, kargo_no=?, kargo_tarihi=? WHERE id=?", (yeni_d, k_no, k_tar, s_id))
                        conn.commit()
                        log_ekle(mevcut_user, f"{len(ids)} adet kayıt '{yeni_d}' durumuna çekildi.")
                        st.success("Güncelleme yapıldı!")
                        st.rerun()

    elif secim == "📂 Yeni Kayıt / Aktar":
        t1, t2 = st.tabs(["✍️ Tekil Kayıt", "📂 Excel'den Toplu Aktar"])
        with t1:
            with st.form("tek_ekle"):
                s = st.text_input("Sicil No")
                a = st.text_input("Ad Soyad")
                u = st.text_area("Ürünler")
                if st.form_submit_button("Kaydet"):
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, urunler, durum, tarih) VALUES (?,?,?,?,?)",
                              (s, a, u, "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y")))
                    conn.commit()
                    log_ekle(mevcut_user, f"Yeni kayıt eklendi: {a}")
                    st.success("Başarıyla eklendi!")
        with t2:
            st.info("⚠️ Excel sütunları: sicil_no, uye_adi, urunler, adet")
            up = st.file_uploader("Excel Dosyası Seçin", type=['xlsx'])
            if up:
                df_up = pd.read_excel(up)
                df_up.columns = df_up.columns.str.strip().str.lower()
                if st.button("Verileri Veritabanına Yaz"):
                    for _, r in df_up.iterrows():
                        c.execute("INSERT INTO siparisler (sicil_no, uye_adi, urunler, adet, durum, tarih) VALUES (?,?,?,?,?,?)",
                                  (str(r.get('sicil_no','')), str(r.get('uye_adi','')), str(r.get('urunler','')), int(r.get('adet', 1)), "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y")))
                    conn.commit()
                    log_ekle(mevcut_user, f"Excel'den toplu veri yüklendi.")
                    st.success("Aktarım tamamlandı!")

    elif secim == "📊 Veri Yönetimi":
        st.subheader("📥 Veri Yedekleme ve Güvenlik")
        df_out = pd.read_sql_query("SELECT * FROM siparisler", conn)
        
        # Excel İndirme
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_out.to_excel(writer, index=False)
        st.download_button("💾 Tüm Veritabanını Excel Olarak Yedekle", output.getvalue(), "fb_lojistik_yedek.xlsx")

        st.divider()
        if st.session_state['yetki'] == "Yönetici":
            st.warning("Tehlikeli Bölge: Veritabanını sıfırlamak tüm verileri kalıcı olarak siler.")
            if st.button("VERİTABANINI TAMAMEN SIFIRLA", type="primary"):
                # Güvenlik önlemi olarak buraya bir onay kutusu ekleyebilirsin
                st.error("Bu işlem şu an devre dışı bırakıldı. Lütfen manuel yapın.")
        else:
            st.info("Veri yönetimi yetkisi sadece yöneticilerdedir.")

    elif secim == "🕒 İşlem Geçmişi":
        st.header("🕒 Son İşlemler")
        st.dataframe(pd.read_sql_query("SELECT * FROM islem_gecmisi ORDER BY id DESC LIMIT 500", conn), use_container_width=True)

    if st.sidebar.button("🚪 Güvenli Çıkış"):
        del st.session_state['kullanici']
        st.rerun()
