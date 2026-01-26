import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. GİRİŞ EKRANI FONKSİYONU ---
def login():
    st.sidebar.title("Kullanıcı Girişi")
    username = st.sidebar.text_input("Kullanıcı Adı")
    password = st.sidebar.text_input("Şifre", type="password")
    
    # Buradaki bilgileri kendi kullanıcı adın ve şifrenle değiştirebilirsin
    if st.sidebar.button("Giriş Yap"):
        if username == "admin" and password == "12345":
            st.session_state['logged_in'] = True
            st.success("Başarıyla giriş yapıldı!")
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı!")

# --- 2. ANA UYGULAMA FONKSİYONU ---
def main_app():
    st.title("🚀 FB Lojistik Takip Sistemi")
    
    # Çıkış butonu
    if st.sidebar.button("Çıkış Yap"):
        st.session_state['logged_in'] = False
        st.rerun()

    uploaded_file = st.file_uploader("Excel Dosyasını Yükleyin", type=['xlsx'])

    if uploaded_file:
        # Veriyi oku ve sütun isimlerini temizle (KeyError önleyici)
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()
        
        st.subheader("🔍 Toplu Arama")
        search_input = st.text_area(
            "Aranacak Sicil Numaralarını girin (Alt alta yapıştırın):",
            placeholder="Örn:\n101202\n103405",
            help="Excel'den bir sütunu kopyalayıp buraya yapıştırabilirsiniz."
        )

        if search_input:
            # Girişi listeye çevir
            search_list = [item.strip() for item in search_input.replace(',', '\n').split('\n') if item.strip()]
            
            # Filtreleme (Tip uyuşmazlığını önlemek için her iki tarafı string yapıyoruz)
            sonuclar = df[df['sicil_no'].astype(str).isin(search_list)]
            
            st.info(f"Toplam {len(sonuclar)} kayıt filtrelendi.")
            st.dataframe(sonuclar)

            if st.button("Seçili Kayıtları Hazırlanıyor Olarak İşle"):
                for index, r in sonuclar.iterrows():
                    # r.get(key, default) kullanımı sayesinde sütun eksikse bile kod çökmez
                    sicil = str(r.get('sicil_no', 'N/A'))
                    uye = str(r.get('uye_adi', 'Bilinmiyor'))
                    # 145. satırdaki kayıt mantığın:
                    st.write(f"✅ İşlendi: {sicil} - {uye} - Durum: Hazırlanıyor")
        else:
            st.write("Dosya İçeriği (İlk 5 Satır):")
            st.table(df.head())

# --- 3. ÇALIŞTIRMA MANTIĞI ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    login()
else:
    main_app()
