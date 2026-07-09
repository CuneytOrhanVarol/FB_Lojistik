from datetime import datetime
import streamlit as st
from aktarim import kayit_ekle_aktar, verileri_getir

st.set_page_config(page_title="FB Lojistik - Üye Sipariş Takip", layout="wide")

st.title("📦 Üye Sipariş Takip Sistemi")
st.write(
    "Yeni üye siparişi/kiti ekleyebilir ve mevcut gönderimleri takip edebilirsiniz."
)

# Yan Menü (Sidebar) - Yeni Kayıt Girişi
st.sidebar.header("📝 Yeni Üye Siparişi Ekle")

with st.sidebar.form(key="siparis_formu", clear_on_submit=True):
    siparis_id = st.text_input("Sipariş No / ID")
    uye_no = st.text_input("Üye No")  # Yeni eklenen alan
    uye_adi = st.text_input("Üye Adı Soyadı")  # İsmi değişen alan

    # Sizin belirttiğiniz yeni ürün listesi
    urunler = [
        "Üyelik Kiti",
        "Üyelik Rozeti",
        "Üyelik Sertifikası",
        "Üyelik Kartı",
        "Üyelik Tişörtü",
        "Üyelik Kristal Plaket",
    ]
    urun = st.selectbox("Ürün Seçin", urunler)

    adet = st.number_input("Adet", min_value=1, value=1)
    durum = st.selectbox(
        "Sipariş Durumu", ["Hazırlanıyor", "Yolda", "Teslim Edildi"]
    )
    tarih = st.date_input("Tarih", datetime.now())

    gonder_butonu = st.form_submit_button(label="Siparişi Kaydet")

# Form gönderildiğinde çalışacak kısım
if gonder_butonu:
    if siparis_id and uye_no and uye_adi:
        # aktarim.py içindeki güncel fonksiyonu çağırıyoruz
        kayit_ekle_aktar(
            siparis_id,
            uye_no,
            uye_adi,
            urun,
            adet,
            durum,
            tarih.strftime("%Y-%m-%d"),
        )
        st.sidebar.success(f"{siparis_id} nolu sipariş başarıyla eklendi!")
    else:
        st.sidebar.error("Lütfen gerekli alanları (ID, Üye No, İsim) doldurun.")

# Ana Ekran - Siparişleri Listeleme
st.subheader("📊 Güncel Üye Gönderim Listesi")
df_siparisler = verileri_getir()

if not df_siparisler.empty:
    # Siparişleri streamlit üzerinde tablo olarak gösteriyoruz
    st.dataframe(df_siparisler, use_container_width=True)

    # Basit istatistikler
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Kayıt", len(df_siparisler))
    col2.metric(
        "Teslim Edilenler", len(df_siparisler[df_siparisler["Durum"] == "Teslim Edildi"])
    )
    col3.metric("Toplam Ürün Adedi", int(df_siparisler["Adet"].sum()))
else:
    st.info("Henüz kaydedilmiş bir üye siparişi bulunmuyor.")
