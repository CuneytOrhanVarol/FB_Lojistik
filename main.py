from datetime import datetime
import pandas as pd
import streamlit as st
from aktarim import kayit_ekle_aktar, verileri_getir

# 1. Sayfa Ayarları
st.set_page_config(page_title="FB Lojistik - Üye Sipariş Takip", layout="wide")

st.title("📦 Üye Sipariş Takip Sistemi")
st.write(
    "Yeni üye siparişi/kiti ekleyebilir ve mevcut gönderimleri takip edebilirsiniz."
)

# 2. Yan Menü (Sidebar) - Tekli Yeni Kayıt Girişi
st.sidebar.header("📝 Yeni Üye Siparişi Ekle")

with st.sidebar.form(key="siparis_formu", clear_on_submit=True):
    siparis_id = st.text_input("Sipariş No / ID")
    uye_no = st.text_input("Üye No")
    uye_adi = st.text_input("Üye Adı Soyadı")

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
    kargo_no = st.text_input("Kargo Takip No")  # Yeni eklenen input alanı
    tarih = st.date_input("Tarih", datetime.now())

    gonder_butonu = st.form_submit_button(label="Siparişi Kaydet")

# Form gönderildiğinde çalışacak kısım
if gonder_butonu:
    if siparis_id and uye_no and uye_adi:
        # Fonksiyona kargo_no argümanını da gönderiyoruz
        kayit_ekle_aktar(
            siparis_id,
            uye_no,
            uye_adi,
            urun,
            adet,
            durum,
            kargo_no,
            tarih.strftime("%Y-%m-%d"),
        )
        st.sidebar.success(f"{siparis_id} nolu sipariş başarıyla eklendi!")
    else:
        st.sidebar.error("Lütfen gerekli alanları (ID, Üye No, İsim) doldurun.")

# 3. Ana Ekran - Siparişleri Listeleme
st.subheader("📊 Güncel Üye Gönderim Listesi")
df_siparisler = verileri_getir()

if not df_siparisler.empty:
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

# 4. Ana Ekranın En Altı - Toplu Veri Aktarım Alanı
st.markdown("---")
st.subheader("📥 Excel'den Toplu Veri Aktarımı")
st.write(
    "Elinizdeki mevcut Excel dosyasını yükleyerek sisteme toplu aktarım yapabilirsiniz."
)

# Sütun uyarı metnine Kargo Takip No eklendi
yuklenen_dosya = st.file_uploader(
    "Sütunları 'Sipariş ID, Üye No, Üye Adı Soyadı, Ürün, Adet, Durum, Kargo Takip No, Tarih' olan Excel dosyasını seçin",
    type=["xlsx"],
)

if yuklenen_dosya is not None:
    try:
        df_yuklenen = pd.read_excel(yuklenen_dosya)

        # Kontrol edilecek listeye Kargo Takip No eklendi
        gerekli_sutunlar = [
            "Sipariş ID",
            "Üye No",
            "Üye Adı Soyadı",
            "Ürün",
            "Adet",
            "Durum",
            "Kargo Takip No",
            "Tarih",
        ]
        eksik_sutunlar = [
            sut for sut in gerekli_sutunlar if sut not in df_yuklenen.columns
        ]

        if eksik_sutunlar:
            st.error(
                f"Yüklediğiniz dosyada şu sütunlar eksik: {', '.join(eksik_sutunlar)}"
            )
            st.warning(
                f"Lütfen Excel dosyanızdaki sütun isimlerini tam olarak şöyle düzenleyin: {', '.join(gerekli_sutunlar)}"
            )
        else:
            st.write("Yüklenecek Veri Önizlemesi:")
            st.dataframe(df_yuklenen.head(), use_container_width=True)

            yontem = st.radio(
                "Aktarım Yöntemi Seçin:",
                (
                    "Mevcut verilerin sonuna ekle (Üzerine yazma)",
                    "Mevcut verileri sil, sadece bu dosyayı kaydet",
                ),
            )

            aktar_butonu = st.button("Verileri Sisteme Aktar")

            if aktar_butonu:
                if yontem == "Mevcut verilerin sonuna ekle (Üzerine yazma)":
                    df_mevcut = verileri_getir()
                    df_son = pd.concat(
                        [df_mevcut, df_yuklenen], ignore_index=True
                    )
                    df_son.to_excel("siparisler.xlsx", index=False)
                else:
                    df_yuklenen.to_excel("siparisler.xlsx", index=False)

                st.success("🎉 Veriler başarıyla aktarıldı!")
                st.rerun()

    except Exception as e:
        st.error(f"Dosya okunurken bir hata oluştu: {e}")
