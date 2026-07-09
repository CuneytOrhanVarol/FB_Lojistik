from datetime import datetime
import pandas as pd
import streamlit as st
from aktarim import kayit_ekle_aktar, verileri_getir

# 1. Sayfa Ayarları
st.set_page_config(page_title="FB Lojistik - Üye Sipariş Takip", layout="wide")

st.title("📦 Üye Sipariş Takip Sistemi")

# 2. YAN MENÜ (SIDEBAR) - SADECE ARAMA VE FİLTRELEME (Form Dışında)
st.sidebar.header("🔍 Sipariş Ara / Filtrele")
st.sidebar.write("Kutulara yazdıktan sonra Enter'a basabilir veya boşluğa tıklayabilirsiniz.")

# Arama kutuları (Kesinlikle bir form içinde DEĞİLLER, tetikleme yapmazlar)
ara_siparis_id = st.sidebar.text_input("Sipariş No / ID ile Ara").strip()
ara_uye_no = st.sidebar.text_input("Üye No ile Ara").strip()
ara_uye_adi = st.sidebar.text_input("Üye Adı Soyadı ile Ara").strip()

urun_secenekleri = ["Hepsi", "Üyelik Kiti", "Üyelik Rozeti", "Üyelik Sertifikası", "Üyelik Kartı", "Üyelik Tişörtü", "Üyelik Kristal Plaket"]
# Artık selectbox yerine multiselect kullanıyoruz ve varsayılan olarak boş (yani hepsi) geliyor
urun_secenekleri = [
    "Üyelik Kiti",
    "Üyelik Rozeti",
    "Üyelik Sertifikası",
    "Üyelik Kartı",
    "Üyelik Tişörtü",
    "Üyelik Kristal Plaket",
]
ara_urunler = st.sidebar.multiselect(
    "Ürünlere Göre Filtrele (Birden Fazla Seçilebilir)", urun_secenekleri
)

durum_secenekleri = ["Hepsi", "Hazırlanıyor", "Yolda", "Teslim Edildi"]
ara_durum = st.sidebar.selectbox("Duruma Göre Filtrele", durum_secenekleri)

st.sidebar.markdown("---")

# 3. YAN MENÜ - Yeni Kayıt Ekleme Butonu (Tamamen Ayrı Bir Bölüm)
with st.sidebar.expander("📝 Yeni Üye Siparişi Ekle"):
    # Bu form artık yukarıdaki arama kutularını etkileyemez
    with st.form(key="gercek_kayit_formu", clear_on_submit=True):
        yeni_id = st.text_input("Sipariş No / ID*")
        yeni_uye_no = st.text_input("Üye No*")
        yeni_adi = st.text_input("Üye Adı Soyadı*")
        yeni_urun = st.selectbox("Ürün*", urun_secenekleri[1:]) # "Hepsi" hariç
        yeni_adet = st.number_input("Adet", min_value=1, value=1)
        yeni_durum = st.selectbox("Sipariş Durumu", durum_secenekleri[1:]) # "Hepsi" hariç
        yeni_kargo = st.text_input("Kargo Takip No")
        yeni_tarih = st.date_input("Tarih", datetime.now())
        
        kaydet_butonu = st.form_submit_button("Siparişi Kaydet")
        
        if kaydet_butonu:
            if yeni_id and yeni_uye_no and yeni_adi:
                kayit_ekle_aktar(yeni_id, yeni_uye_no, yeni_adi, yeni_urun, yeni_adet, yeni_durum, yeni_kargo, yeni_tarih.strftime('%Y-%m-%d'))
                st.success("Kayıt başarıyla eklendi!")
                st.rerun()
            else:
                st.error("Yıldızlı (*) alanlar zorunludur!")

# 4. ANA EKRAN - Filtrelenmiş Verileri Listeleme
st.subheader("📊 Üye Gönderim Listesi")
df_siparisler = verileri_getir()

if not df_siparisler.empty:
    df_filtrelenmis = df_siparisler.copy()
    
    # Güçlendirilmiş ve boşluklardan arındırılmış veri arama motoru
    if ara_siparis_id:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis["Sipariş ID"].astype(str).str.strip().str.contains(ara_siparis_id, case=False, na=False)]
        
    if ara_uye_no:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis["Üye No"].astype(str).str.strip().str.contains(ara_uye_no, case=False, na=False)]
        
    if ara_uye_adi:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis["Üye Adı Soyadı"].astype(str).str.strip().str.contains(ara_uye_adi, case=False, na=False)]
        
    if ara_urun != "Hepsi":
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis["Ürün"] == ara_urun]
        
    if ara_durum != "Hepsi":
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis["Durum"] == ara_durum]

    # Sonuçları göster
    st.dataframe(df_filtrelenmis, use_container_width=True)

    # İstatistikler
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Listelenen Kayıt", len(df_filtrelenmis))
    col2.metric("Teslim Edilenler", len(df_filtrelenmis[df_filtrelenmis["Durum"] == "Teslim Edildi"]))
    col3.metric("Toplam Ürün Adedi", int(df_filtrelenmis["Adet"].sum()) if not df_filtrelenmis.empty else 0)
else:
    st.info("Henüz kaydedilmiş bir üye siparişi bulunmuyor.")

# 5. Toplu Veri Aktarım Alanı
st.markdown("---")
st.subheader("📥 Excel'den Toplu Veri Aktarımı")
yuklenen_dosya = st.file_uploader("Sütunları 'Sipariş ID, Üye No, Üye Adı Soyadı, Ürün, Adet, Durum, Kargo Takip No, Tarih' olan Excel dosyasını seçin", type=["xlsx"])

if yuklenen_dosya is not None:
    try:
        df_yuklenen = pd.read_excel(yuklenen_dosya)
        gerekli_sutunlar = ["Sipariş ID", "Üye No", "Üye Adı Soyadı", "Ürün", "Adet", "Durum", "Kargo Takip No", "Tarih"]
        eksik_sutunlar = [sut for sut in gerekli_sutunlar if sut not in df_yuklenen.columns]
        
        if eksik_sutunlar:
            st.error(f"Eksik sütunlar var: {', '.join(eksik_sutunlar)}")
        else:
            yontem = st.radio("Aktarım Yöntemi:", ("Mevcut verilerin sonuna ekle", "Mevcut verileri sil, bunu kaydet"))
            if st.button("Verileri Sisteme Aktar"):
                if yontem == "Mevcut verilerin sonuna ekle":
                    df_mevcut = verileri_getir()
                    df_son = pd.concat([df_mevcut, df_yuklenen], ignore_index=True)
                    df_son.to_excel("siparisler.xlsx", index=False)
                else:
                    df_yuklenen.to_excel("siparisler.xlsx", index=False)
                st.success("Veriler başarıyla aktarıldı!")
                st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")
