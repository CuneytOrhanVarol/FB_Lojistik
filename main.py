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

c.execute('''CREATE TABLE IF NOT EXISTS islem_gecmisi (
    id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici TEXT, islem TEXT, zaman TEXT)''')
conn.commit()

# --- AYARLAR ---
KULLANICILAR = {"Cüneyt Orhan Varol": "fb01", "Mehmet Erkin Ataş": "fb02", "Ersen Avcı": "fb03", "Simay Önder": "fb04", "Pervin Hanım": "ipek123", "Mevlüt Bey": "ikba456", "Engin Bey": "kuker789"}
YONETICILER = ["Cüneyt Orhan Varol", "Mehmet Erkin Ataş", "Ersen Avcı", "Simay Önder"]
DURUMLAR = ["Hazırlanıyor (Üye İlişkileri)", "Hazırlanıyor (Kuker)", "Hazırlanıyor (İkba Kristal)", "Hazırlanıyor (İpek Kutu)", "Kargoya verildi", "Teslim edildi"]

def log_ekle(kullanici, islem):
    zaman = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    c.execute("INSERT INTO islem_gecmisi (kullanici, islem, zaman) VALUES (?,?,?)", (kullanici, islem, zaman))
    conn.commit()

st.set_page_config(page_title="FB Operasyon v6.3", layout="wide")

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
            st.error("Hatalı şifre!")
else:
    mevcut_user = st.session_state['kullanici']
    st.sidebar.title(f"👤 {mevcut_user}")
    secim = st.sidebar.radio("Menü", ["📦 Operasyon Paneli", "📈 Performans & Finans", "📂 Kayıt Ekle / Aktar", "🗑️ Yönetim", "🕒 Log"])

    if secim == "📦 Operasyon Paneli":
        st.header("🚀 Operasyonel Akış Kontrolü")
        
        # --- VERİ ÇEKME ---
        df_all = pd.read_sql_query("SELECT * FROM siparisler", conn)
        
        if not df_all.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Toplam", len(df_all))
            c2.metric("Üye İlişkileri", len(df_all[df_all['durum'] == DURUMLAR[0]]))
            tedarikci_v = df_all[df_all['durum'].str.contains("Hazırlanıyor", na=False) & ~df_all['durum'].str.contains("Üye", na=False)]
            c3.metric("Tedarikçiler", len(tedarikci_v))
            c4.metric("Kargo/Teslim", len(df_all[df_all['durum'].isin(["Kargoya verildi", "Teslim edildi"])]))

            st.divider()

            # --- ARAMA ---
            col_a, col_b = st.columns([2, 1])
            s_query = col_a.text_input("🔍 Hızlı Bul (İsim, Sicil veya Telefon)")
            s_status = col_b.selectbox("Durum Filtresi", ["Tümü"] + DURUMLAR)

            query = "SELECT * FROM siparisler WHERE 1=1"
            params = []
            if s_query:
                query += " AND (uye_adi LIKE ? OR sicil_no LIKE ? OR telefon_no LIKE ?)"
                params.extend([f"%{s_query}%"]*3)
            if s_status != "Tümü":
                query += " AND durum = ?"; params.append(s_status)
            
            df = pd.read_sql_query(query + " ORDER BY id DESC", conn, params=params)

            if not df.empty:
                st.write("### 📝 İşlem Bekleyen Kayıtlar")
                st.caption("Güncellemek istediğiniz kişilerin yanındaki kutucuğu işaretleyin.")
                
                # --- ÇÖKMEYİ ÖNLEYEN YENİ TABLO YAPISI ---
                df.insert(0, "Seç", False) # En başa seçim kutusu ekle
                
                
                
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "Seç": st.column_config.CheckboxColumn("Seç", default=False),
                        "id": None, # ID'yi gizle ama arkada tut
                        "kargo_no": "Kargo No",
                        "birim_maliyet": None # Operasyon panelinde maliyeti gizle
                    },
                    disabled=["id", "sicil_no", "uye_adi", "durum", "tarih", "telefon_no", "urunler"], 
                    use_container_width=True,
                    hide_index=True,
                    key="op_editor"
                )

                # Seçilen ID'leri filtrele
                selected_ids = edited_df[edited_df['Seç'] == True]['id'].tolist()
                
                if selected_ids:
                    st.subheader(f"⚡ Seçilen {len(selected_ids)} Kaydı Şuraya Gönder:")
                    btn_cols = st.columns(len(DURUMLAR))
                    for i, d_adi in enumerate(DURUMLAR):
                        # Buton etiketlerini sadeleştirelim
                        label = d_adi.split("(")[-1].replace(")", "") if "(" in d_adi else d_adi
                        if btn_cols[i].button(label, key=f"btn_{i}"):
                            for s_id in selected_ids:
                                c.execute("UPDATE siparisler SET durum=? WHERE id=?", (d_adi, s_id))
                            conn.commit()
                            log_ekle(mevcut_user, f"{len(selected_ids)} kayıt '{d_adi}' yapıldı.")
                            st.success("İşlem Başarılı!")
                            st.rerun()
            else:
                st.warning("Aranan kriterlerde kayıt bulunamadı.")
        else:
            st.info("Sistemde henüz kayıtlı sipariş yok.")

    # --- PERFORMANS / YENİ KAYIT / YÖNETİM ---
    elif secim == "📈 Performans & Finans":
        st.header("📈 Analitik Özet")
        df_p = pd.read_sql_query("SELECT * FROM siparisler", conn)
        if not df_p.empty:
            col_g1, col_g2 = st.columns(2)
            fig_bar = px.bar(df_p.groupby('durum').size().reset_index(name='Sayı'), x='durum', y='Sayı', color='durum', title="Yük Dağılımı")
            col_g1.plotly_chart(fig_bar, use_container_width=True)
            
            df_p['tarih_dt'] = pd.to_datetime(df_p['tarih'], dayfirst=True, errors='coerce')
            daily = df_p.groupby('tarih_dt').size().reset_index(name='Adet')
            fig_line = px.line(daily, x='tarih_dt', y='Adet', markers=True, title="Kayıt Giriş Trendi")
            col_g2.plotly_chart(fig_line, use_container_width=True)

    elif secim == "📂 Kayıt Ekle / Aktar":
        t1, t2 = st.tabs(["✍️ Manuel Ekle", "📂 Excel Aktar"])
        with t1:
            with st.form("manuel_form"):
                s = st.text_input("Sicil"); a = st.text_input("Ad Soyad"); tel = st.text_input("Telefon"); u = st.text_area("Ürünler")
                if st.form_submit_button("Kaydet"):
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, telefon_no, urunler, durum, tarih) VALUES (?,?,?,?,?,?)", (s,a,tel,u, DURUMLAR[0], datetime.now().strftime("%d/%m/%Y")))
                    conn.commit(); st.success("Eklendi!"); st.rerun()
        with t2:
            up = st.file_uploader("Dosya Seç", type=['xlsx'])
            if up and st.button("Excel'den Çek"):
                df_up = pd.read_excel(up)
                for _, r in df_up.iterrows():
                    c.execute("INSERT INTO siparisler (sicil_no, uye_adi, telefon_no, urunler, durum, tarih) VALUES (?,?,?,?,?,?)", (str(r.get('sicil_no','')), str(r.get('uye_adi','')), str(r.get('telefon_no','')), str(r.get('urunler','')), DURUMLAR[0], datetime.now().strftime("%d/%m/%Y")))
                conn.commit(); st.success("Aktarım Tamamlandı!"); st.rerun()

    elif secim == "🗑️ Yönetim":
        if st.session_state['yetki'] == "Yönetici":
            st.subheader("🗑️ Kayıt Yönetimi")
            df_del = pd.read_sql_query("SELECT id, sicil_no, uye_adi FROM siparisler", conn)
            sel_del = st.multiselect("Silinecek ID'ler", df_del['id'].tolist())
            if st.button("Seçilenleri Sil"):
                for i in sel_del: c.execute("DELETE FROM siparisler WHERE id=?", (i,))
                conn.commit(); st.rerun()
        else: st.warning("Bu alana erişim yetkiniz yok.")

    elif secim == "🕒 Log":
        st.dataframe(pd.read_sql_query("SELECT * FROM islem_gecmisi ORDER BY id DESC", conn), use_container_width=True)

    if st.sidebar.button("🚪 Çıkış"):
        del st.session_state['kullanici']; st.rerun()
