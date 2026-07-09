ImportError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:
File "/mount/src/fb_lojistik/main.py", line 6, in <module>
    from aktarim import kayit_ekle_aktar
from datetime import datetime
import streamlit as st
# Sizin kodunuzda hata veren kritik import satırı:
from aktarim import kayit_ekle_aktar, verileri_getir

st.set_page_config(page_title="FB Lojistik - Sipariş Takip", layout="wide")

st.title("📦 Lojistik Sipariş Takip Sistemi")
st.write("Yeni sipariş ekleyebilir ve mevcut siparişleri görebilirsiniz.")

# Yan Menü (Sidebar) - Yeni Sipariş Girişi
st.sidebar.header("📝 Yeni Sipariş Ekle")

with st.sidebar.form(key="siparis_formu", clear_on_submit=True):
    siparis_id = st.text_input("Sipariş No / ID")
    musteri = st.text_input("Müşteri Adı")
    urun = st.selectbox(
        "Ürün Seçin", ["Elektronik", "Tekstil", "Gıda", "Yedek Parça"]
    )
    adet = st.number_input("Adet", min_value=1, value=1)
    durum = st.selectbox(
        "Sipariş Durumu", ["Hazırlanıyor", "Yolda", "Teslim Edildi"]
    )
    tarih = st.date_input("Tarih", datetime.now())

    gonder_butonu = st.form_submit_button(label="Siparişi Kaydet")

# Form gönderildiğinde çalışacak kısım
if gonder_butonu:
    if siparis_id and musteri:
        # aktarim.py içindeki fonksiyonu çağırıyoruz
        kayit_ekle_aktar(
            siparis_id, musteri, urun, adet, durum, tarih.strftime("%Y-%m-%d")
        )
        st.sidebar.success(f"{siparis_id} nolu sipariş başarıyla eklendi!")
    else:
        st.sidebar.error("Lütfen Sipariş ID ve Müşteri Adı alanlarını doldurun.")

# Ana Ekran - Siparişleri Listeleme
st.subheader("📊 Güncel Sipariş Listesi")
df_siparisler = verileri_getir()

if not df_siparisler.empty:
    # Siparişleri streamlit üzerinde tablo olarak gösteriyoruz
    st.dataframe(df_siparisler, use_container_width=True)

    # Basit istatistikler
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Sipariş", len(df_siparisler))
    col2.metric(
        "Teslim Edilenler", len(df_siparisler[df_siparisler["Durum"] == "Teslim Edildi"])
    )
    col3.metric("Toplam Ürün Adedi", int(df_siparisler["Adet"].sum()))
else:
    st.info("Henüz kaydedilmiş bir sipariş bulunmuyor.")
