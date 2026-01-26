import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# --- VERİTABANI BAĞLANTISI ---
conn = sqlite3.connect('fb_operasyon_merkezi_v2.db', check_same_thread=False)
c = conn.cursor()

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

# --- ARAYÜZ ---
st.set_page_config(page_title="FB Kongre Lojistik Paneli", layout="wide")

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
    st.sidebar.info(f"Yetki: {st.session_state['yetki']}")
    
    secim = st.sidebar.radio("Menü", ["Sipariş Takip / Operasyon", "Yeni Kayıt & İçeri Aktar", "Kayıt Silme İşlemleri", "İşlem Geçmişi (Log)", "Dışarı Aktar"])

    if secim == "Sipariş Takip / Operasyon":
        st.header("🚀 Operasyonel İş Akışı")

        # --- İŞ AKIŞI DASHBOARD (GÖRSEL ÖZET) ---
        stats = pd.read_sql_query("SELECT durum, COUNT(*) as sayi FROM siparisler GROUP BY durum", conn)
        stat_dict = dict(zip(stats['durum'], stats['sayi']))
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Hazırlanan", stat_dict.get("Hazırlanıyor", 0))
        c2.metric("🛠️ Tedarikçide", stat_dict.get("Kuker hazırlıyor", 0) + stat_dict.get("İKBA Kristal hazırlıyor", 0))
        c3.metric("🚚 Kargoda", stat_dict.get("Kargoda", 0))
        c4.metric("✅ Tamamlanan", stat_dict.get("Tamamlandı", 0))
        
        st.divider()

        # --- FİLTRELEME ---
        with st.expander("🔍 Detaylı ve Toplu Arama Paneli", expanded=True):
            col1, col2 = st.columns([1, 2])
            with col1:
                search_name = st.text_input("İsim Soyad'a göre ara")
                # Tedarikçiler için varsayılan durum atama
                default_status = "Tümü"
                if mevcut_user == "Pervin Hanım": default_status = "İpek Kutu'ya gönderildi"
                elif mevcut_user == "Mevlüt Bey": default_status = "İKBA Kristal hazırlıyor"
                elif mevcut_user == "Engin Bey": default_status = "Kuker hazırlıyor"
                
                search_status = st.selectbox("Durum Filtrele", ["Tümü"] + DURUMLAR, index=0 if default_status=="Tümü" else DURUMLAR.index(default_status)+1)
            with col2:
                search_sicil_bulk = st.text_area("Toplu Sicil No Sorgulama (Alt alta yapıştırın)")

        # --- SQL SORGUSU ---
        query = "SELECT id as 'ID', sicil_no as 'Sicil No', uye_adi as 'Ad Soyad', urunler as 'Ürünler', adet as 'Adet', durum as 'Durum', kargo_no as 'Kargo No', kargo_tarihi as 'Kargo Tarihi', tarih as 'Kayıt Tarihi' FROM siparisler WHERE 1=1"
        params = []
        
        if search_sicil_bulk:
            siciller = [s.strip() for s in search_sicil_bulk.replace('\n', ',').split(',') if s.strip()]
            if siciller:
                placeholders = ','.join(['?'] * len(siciller))
                query += f" AND sicil_no IN ({placeholders})"
                params.extend(siciller)
        if search_name:
            query += " AND uye_adi LIKE ?"
            params.append(f"%{search_name}%")
        if search_status != "Tümü":
            query += " AND durum = ?"
            params.append(search_status)
            
        df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # --- GÜNCELLEME FORMU ---
            with st.form("güncelleme_formu"):
                st.subheader("🛠️ Toplu İşlem Yap")
                df['secim_etiketi'] = df['Sicil No'].astype(str) + " - " + df['Ad Soyad'] + " (ID: " + df['ID'].astype(str) + ")"
                etiket_to_id = dict(zip(df['secim_etiketi'], df['ID']))
                
                c1, c2 = st.columns(2)
                secilen_etiketler = c1.multiselect("İşlem Yapılacak Kayıtlar", df['secim_etiketi'].tolist())
                yeni_statü = c2.selectbox("Yeni Durum", DURUMLAR)
                
                c3, c4 = st.columns(2)
                yeni_kargo_no = c3.text_input("Kargo No (Varsa)")
                yeni_kargo_tarih = c4.text_input("Kargo Tarihi (Varsa)")
                
                if st.form_submit_button("Seçili Kayıtları Güncelle"):
                    if secilen_etiketler:
                        ids = [etiket_to_id[e] for e in secilen_etiketler]
                        for s_id in ids:
                            c.execute("UPDATE siparisler SET durum = ?, kargo_no = ?, kargo_tarihi = ? WHERE id = ?", (yeni_statü, yeni_kargo_no, yeni_kargo_tarih, s_id))
                        conn.commit()
                        log_ekle(mevcut_user, f"{len(ids)} kaydı '{yeni_statü}' yaptı.")
                        st.success("İşlem başarılı!")
                        st.rerun()
        else:
            st.warning("Gösterilecek kayıt bulunamadı.")

    elif secim == "Yeni Kayıt & İçeri Aktar":
        t1, t2 = st.tabs(["✍️ Tekil Kayıt", "📂 Excel Yükle"])
        with t1:
            with st.form("tekil"):
                f_sicil = st.text_input("Sicil No")
                f_ad = st.text_input("Ad Soyad")
                f_urun = st.text_area("Ürünler")
                f_adet = st.number_input("Adet", min_value=1, value=1)
                if st.form_submit_button("Kaydet"):
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, urunler, adet, durum, tarih) VALUES (?,?,?,?,?,?)",
                              (f_sicil, f_ad, f_urun, f_adet, "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y")))
                    conn.commit()
                    log_ekle(mevcut_user, f"Yeni kayıt: {f_ad}")
                    st.success("Eklendi!")
        with t2:
            st.info("💡 Sütunlar: sicil_no, uye_adi, urunler, adet (Küçük harf ve boşluksuz olması önerilir)")
            up_file = st.file_uploader("Excel Seç", type=['xlsx'])
            if up_file:
                df_up = pd.read_excel(up_file)
                # OTOMATİK DÜZELTME: Sütun isimlerini temizle
                df_up.columns = df_up.columns.str.strip().str.lower()
                
                if st.button("Aktarımı Başlat"):
                    for _, r in df_up.iterrows():
                        # .get() ile hata koruması
                        c.execute("INSERT INTO siparisler (sicil_no, uye_adi, urunler, adet, durum, tarih) VALUES (?,?,?,?,?,?)",
                                  (str(r.get('sicil_no','')), str(r.get('uye_adi','')), str(r.get('urunler','')), int(r.get('adet', 1)), "Hazırlanıyor", datetime.now().strftime("%d/%m/%Y")))
                    conn.commit()
                    log_ekle(mevcut_user, f"Excel'den toplu aktarım yaptı.")
                    st.success("Başarıyla aktarıldı!")
                    st.rerun()

    # --- DİĞER MENÜLER (KODUNUN ORİJİNAL HALİ KORUNDU) ---
    elif secim == "Kayıt Silme İşlemleri":
        if st.session_state['yetki'] == "Yönetici":
            st.header("🗑️ Kayıt Silme Paneli")
            df_sil = pd.read_sql_query("SELECT id, sicil_no, uye_adi FROM siparisler", conn)
            df_sil['etiket'] = df_sil['sicil_no'].astype(str) + " - " + df_sil['uye_adi']
            etiket_dict = dict(zip(df_sil['etiket'], df_sil['id']))
            secilenler = st.multiselect("Silinecekleri Seç", df_sil['etiket'].tolist())
            if st.button("Seçilenleri Sil"):
                for e in secilenler:
                    c.execute("DELETE FROM siparisler WHERE id = ?", (etiket_dict[e],))
                conn.commit()
                log_ekle(mevcut_user, f"{len(secilenler)} kayıt sildi.")
                st.error("Kayıtlar silindi!")
                st.rerun()
        else:
            st.warning("Bu alanı sadece yöneticiler kullanabilir.")

    elif secim == "Dışarı Aktar":
        df_out = pd.read_sql_query("SELECT * FROM siparisler", conn)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_out.to_excel(writer, index=False, sheet_name='Siparişler')
        st.download_button("📥 Excel İndir", output.getvalue(), f"fb_lojistik_{datetime.now().strftime('%Y%m%d')}.xlsx")

    elif secim == "İşlem Geçmişi (Log)":
        st.dataframe(pd.read_sql_query("SELECT zaman, kullanici, islem FROM islem_gecmisi ORDER BY id DESC", conn), use_container_width=True)

    if st.sidebar.button("🚪 Güvenli Çıkış"):
        del st.session_state['kullanici']
        st.rerun()
