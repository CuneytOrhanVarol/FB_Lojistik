import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. KULLANICI VERİTABANI ---
# Eski şifreleri ve kullanıcıları buraya tanımladık
USERS = {
    "Cüneyt Orhan Varol": "fb01",
    "Mehmet Erkin Ataş": "fb02"
}

# --- 2. GİRİŞ EKRANI ---
def login():
    st.set_page_config(page_title="FB Lojistik Giriş", layout="centered")
    
    # Görsel olarak daha şık bir giriş paneli
    st.title("🛡️ FB Lojistik Yönetim Paneli")
    
    with st.container():
        st.write("Lütfen devam etmek için kimlik bilgilerinizi giriniz.")
        username = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type="password")
        
        if st.button("Sisteme Giriş Yap"):
            if username in USERS and USERS[username] == password:
                st.session_state['logged_in'] = True
                st.session_state['user_name'] = username
                st.success(f"Hoş geldiniz, {username}!")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı. Lütfen tekrar deneyin.")

# --- 3. ANA UYGULAMA PANELİ ---
def main_app():
    st.set_page_config(page_title="FB Lojistik Takip", layout="wide")
    
    # Sidebar üzerinde kullanıcı bilgisi ve çıkış
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.title("📦 Lojistik Takip ve Toplu Arama")
    
    uploaded_file = st.file_uploader("Veri dosyasını yükleyin (Excel)", type=['xlsx'])

    if uploaded_file:
        # Veriyi oku ve sütun isimlerini standartlaştır (KeyError önleyici)
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()
        
        st.divider()
        
        # --- TOPLU ARAMA BÖLÜMÜ ---
        st.subheader("🔍 Toplu Arama Sistemi")
        search_input = st.text_area(
            "Aranacak Sicil Numaraları:",
            placeholder="Numaraları buraya alt alta yapıştırın...",
            help="Excel'den kopyaladığınız sicil no sütununu buraya doğrudan yapıştırabilirsiniz."
        )

        if search_input:
            # Girdiyi listeye dönüştürme ve temizleme
            search_list = [item.strip() for item in search_input.replace(',', '\n').split('\n') if item.strip()]
            
            # Veri tipi uyuşmazlığını önlemek için her iki tarafı string yapıp arıyoruz
            sonuclar = df[df['sicil_no'].astype(str).isin(search_list)]
            
            if not sonuclar.empty:
                st.success(f"Toplam {len(sonuclar)} eşleşen kayıt bulundu.")
                st.dataframe(sonuclar, use_container_width=True)
                
                # İşlem yapma butonu
                if st.button("Seçili Kayıtları 'Hazırlanıyor' Olarak İşle"):
                    for _, r in sonuclar.iterrows():
                        # r.get kullanımı sütun eksik olsa da kodun durmasını engeller
                        sicil = str(r.get('sicil_no', 'N/A'))
                        uye = str(r.get('uye_adi', 'Bilinmiyor'))
                        tarih = datetime.now().strftime("%d/%m/%Y")
                        
                        st.write(f"✅ İşlem Tamam: {sicil} | {uye} | Tarih: {tarih}")
            else:
                st.warning("Eşleşen kayıt bulunamadı.")
        else:
            st.info("Arama yapmak için yukarıdaki kutuya sicil numaralarını giriniz.")
            st.write("Yüklenen Dosya Önizlemesi:")
            st.dataframe(df.head(10), use_container_width=True)

# --- 4. ÇALIŞTIRMA MANTIĞI ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    login()
else:
    main_app()
