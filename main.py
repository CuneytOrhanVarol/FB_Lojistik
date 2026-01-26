import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. KULLANICI VERİTABANI ---
USERS = {
    "Cüneyt Orhan Varol": "fb01",
    "Mehmet Erkin Ataş": "fb02"
}

# --- 2. GİRİŞ EKRANI ---
def login():
    st.set_page_config(page_title="FB Lojistik Giriş", layout="centered")
    st.title("🛡️ FB Lojistik Yönetim Paneli")
    
    with st.container():
        username = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type="password")
        
        if st.button("Sisteme Giriş Yap"):
            if username in USERS and USERS[username] == password:
                st.session_state['logged_in'] = True
                st.session_state['user_name'] = username
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı.")

# --- 3. ANA UYGULAMA PANELİ ---
def main_app():
    st.set_page_config(page_title="FB Lojistik Takip", layout="wide")
    
    # --- SİDEBAR (YAN MENÜ) ---
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    
    uploaded_file = st.sidebar.file_uploader("Excel Dosyasını Yükleyin", type=['xlsx'])
    
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state['logged_in'] = False
        st.rerun()

    if uploaded_file:
        # Veriyi oku ve sütun isimlerini temizle
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()

        # --- ESKİ ARAMA SEÇENEKLERİ (SİDEBAR) ---
        st.sidebar.divider()
        st.sidebar.subheader("🔎 Tekli Filtreleme")
        
        # Üye Adı ile Arama
        if 'uye_adi' in df.columns:
            uye_listesi = ["Hepsi"] + sorted(df['uye_adi'].astype(str).unique().tolist())
            secilen_uye = st.sidebar.selectbox("Üye Seçin:", uye_listesi)
        
        # Sicil No ile Arama
        search_sicil = st.sidebar.text_input("Hızlı Sicil Ara:")

        # --- ANA PANEL (TOPLU ARAMA) ---
        st.title("📦 Lojistik İşlem Merkezi")
        
        # Filtreleme Mantığı (Hem Sidebar hem Ana Panel)
        filtered_df = df.copy()
        
        if secilen_uye != "Hepsi":
            filtered_df = filtered_df[filtered_df['uye_adi'] == secilen_uye]
        
        if search_sicil:
            filtered_df = filtered_df[filtered_df['sicil_no'].astype(str).contains(search_sicil)]

        # --- YENİ TOPLU ARAMA ALANI ---
        with st.expander("📋 TOPLU SİCİL ARAMA (Çoklu Sorgu Yapmak İçin Tıklayın)", expanded=True):
            search_input = st.text_area("Sicil Numaralarını buraya alt alta yapıştırın:")
            
            if search_input:
                search_list = [item.strip() for item in search_input.replace(',', '\n').split('\n') if item.strip()]
                filtered_df = df[df['sicil_no'].astype(str).isin(search_list)]

        # --- SONUÇLARI GÖSTER ---
        st.subheader("📊 İşlem Bekleyen Kayıtlar")
        st.write(f"Görüntülenen kayıt sayısı: {len(filtered_df)}")
        st.dataframe(filtered_df, use_container_width=True)

        if not filtered_df.empty:
            if st.button("Listelenen Tüm Kayıtları İşle (Hazırlanıyor)"):
                for _, r in filtered_df.iterrows():
                    # r.get() ile güvenli veri çekme
                    sicil = str(r.get('sicil_no', 'N/A'))
                    uye = str(r.get('uye_adi', 'Bilinmiyor'))
                    st.write(f"✅ Hazırlanıyor: {sicil} - {uye}")
    else:
        st.info("Lütfen sol taraftaki menüden bir Excel dosyası yükleyerek başlayın.")

# --- 4. ÇALIŞTIRMA MANTIĞI ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    login()
else:
    main_app()
