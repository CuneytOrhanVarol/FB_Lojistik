import streamlit as st
import pandas as pd
from datetime import datetime

# --- VERİ YÜKLEME VE HAZIRLIK ---
def load_data(file):
    df = pd.read_excel(file)
    # Sütun isimlerindeki boşlukları temizle ve küçük harfe çevir
    # Böylece 'sicil_no' hatasını bir daha almazsın
    df.columns = df.columns.str.strip().str.lower()
    return df

st.title("FB Lojistik Takip Sistemi")

uploaded_file = st.file_uploader("Excel Dosyasını Yükleyin", type=['xlsx'])

if uploaded_file:
    df = load_data(uploaded_file)
    
    # --- TOPLU ARAMA BÖLÜMÜ ---
    st.subheader("🔍 Toplu Arama")
    
    search_input = st.text_area(
        "Aranacak Sicil Numaralarını girin (Alt alta yapıştırabilir veya virgülle ayırabilirsiniz):",
        placeholder="Örn:\n12345\n67890"
    )

    if search_input:
        # Girişi temizle: Virgülleri satır sonuna çevir, sonra satırlara böl ve boşlukları at
        search_list = [
            item.strip() 
            for item in search_input.replace(',', '\n').split('\n') 
            if item.strip()
        ]
        
        if search_list:
            # Arama yaparken hem veri setindeki hem aranan listedeki değerleri metne (string) çeviriyoruz
            # Bu sayede tip uyuşmazlığı (int vs str) hatası yaşanmaz
            sonuclar = df[df['sicil_no'].astype(str).isin(search_list)]
            
            st.success(f"{len(sonuclar)} kayıt bulundu.")
            st.dataframe(sonuclar)
            
            # Bulunan sonuçları indirme seçeneği (Opsiyonel)
            csv = sonuclar.to_csv(index=False).encode('utf-8')
            st.download_button("Sonuçları CSV Olarak İndir", csv, "arama_sonuclari.csv", "text/csv")
        else:
            st.info("Aramak için numara girin.")
    else:
        st.write("Tüm liste görüntüleniyor (İlk 10 kayıt):")
        st.dataframe(df.head(10))

    # --- SİCİL KAYDETME BÖLÜMÜ (Senin 145. satırdaki mantığın) ---
    st.divider()
    st.subheader("📥 Yeni Kayıt İşleme")
    
    if st.button("Seçili Kayıtları Hazırlanıyor Olarak İşaretle"):
        # Burada arama sonuçlarındaki verileri döngüye alıyoruz
        for index, r in sonuclar.iterrows():
            # .get() kullanarak sütun eksik olsa bile kodun çökmesini engelledik
            sicil = str(r.get('sicil_no', 'N/A'))
            uye = str(r.get('uye_adi', 'Bilinmiyor'))
            urun = str(r.get('urunler', 'Belirtilmemiş'))
            adet = int(r.get('adet', 1))
            tarih = datetime.now().strftime("%d/%m/%Y")
            durum = "Hazırlanıyor"
            
            # Burada veritabanına kaydetme veya listeye ekleme işlemini yapabilirsin
            st.write(f"İşleniyor: {sicil} - {uye}")
