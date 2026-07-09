from datetime import datetime
import io
import pandas as pd
import streamlit as st
from aktarim import kayit_ekle_aktar, verileri_getir, siparis_durum_guncelle

# 1. Sayfa Ayarları
st.set_page_config(page_title="FB Lojistik - Üye Sipariş Takip", layout="wide")

st.title("📦 Üye Sipariş Takip Sistemi")

# 2. YAN MENÜ (SIDEBAR) - SADECE ARAMA VE FİLTRELEME
st.sidebar.header("🔍 Sipariş Ara / Filtrele")
st.sidebar.write(
    "Kutulara yazdıktan sonra Enter'a basabilir veya boşluğa tıklayabilirsiniz."
)

ara_siparis_id = st.sidebar.text_input("Sipariş No / ID ile Ara").strip()
ara_uye_no = st.sidebar.text_input("Üye No ile Ara").strip()
ara_uye_adi = st.sidebar.text_input("Üye Adı Soyadı ile Ara").strip()

urun_secenekleri = [
    "Üyelik Kiti",
    "Üyelik Rozeti",
    "Üyelik Sertifikası",
    "Üyelik Kartı",
    "Üyelik Tişörtü",
    "Üyelik Kristal Plaket",
]
ara_urunler = st.sidebar.multiselect(
    "Ürünlere Göre Filtrele (Çoklu Seçim)", urun_secenekleri
)

durum_secenekleri = ["Hepsi", "Hazırlanıyor", "Yolda", "Teslim Edildi"]
ara_durum = st.sidebar.selectbox("Duruma Göre Filtrele", durum_secenekleri)

st.sidebar.markdown("---")

# 3. YAN MENÜ - Yeni Kayıt Ekleme Butonu
with st.sidebar.expander("📝 Yeni Üye Siparişi Ekle"):
    with st.form(key="gercek_kayit_formu", clear_on_submit=True):
        yeni_id = st.text_input("Sipariş No / ID*")
        yeni_uye_no = st.text_input("Üye No*")
        yeni_adi = st.text_input("Üye Adı Soyadı*")
        yeni_urun = st.selectbox("Ürün*", urun_secenekleri)
        yeni_adet = st.number_input("Adet", min_value=1, value=1)
        yeni_durum = st.selectbox("Sipariş Durumu", durum_secenekleri[1:])
        yeni_kargo = st.text_input("Kargo Takip No")
        yeni_tarih = st.date_input("Tarih", datetime.now())

        kaydet_butonu = st.form_submit_button("Siparişi Kaydet")

        if kaydet_butonu:
            if yeni_id and yeni_uye_no and yeni_adi:
                kayit_ekle_aktar(
                    yeni_id,
                    yeni_uye_no,
                    yeni_adi,
                    yeni_urun,
                    yeni_adet,
                    yeni_durum,
                    yeni_kargo,
                    yeni_tarih.strftime("%Y-%m-%d"),
                )
                st.success("Kayıt başarıyla eklendi!")
                st.rerun()
            else:
                st.error("Yıldızlı (*) alanlar zorunludur!")

# 4. YAN MENÜ - SİPARİŞ DURUMU GÜNCELLEME ALANI
with st.sidebar.expander("🔄 Sipariş Durumu Güncelle"):
    with st.form(key="guncelleme_formu", clear_on_submit=True):
        guncelle_id = st.text_input("Güncellenecek Sipariş ID*")
        guncelle_durum = st.selectbox("Yeni Durum*", durum_secenekleri[1:])
        guncelle_kargo = st.text_input(
            "Yeni Kargo No (Değişmeyecekse Boş Bırakın)"
        )

        guncelle_butonu = st.form_submit_button("Durumu Güncelle")

        if guncelle_butonu:
            if guncelle_id:
                basarili_mi = siparis_durum_guncelle(
                    guncelle_id, guncelle_durum, guncelle_kargo
                )
                if basarili_mi:
                    st.success(
                        f"ID: {guncelle_id} başarıyla '{guncelle_durum}' yapıldı!"
                    )
                    st.rerun()
                else:
                    st.error(
                        f"Sipariş ID ({guncelle_id}) bulunamadı. Lütfen kontrol edin."
                    )
            else:
                st.error("Lütfen Sipariş ID giriniz.")


# 5. KRİTİK GECİKME VE SLA TAKİP SİSTEMİ (Tıklanabilir Pop-up Özelliği Eklendi)
df_siparisler = verileri_getir()

# Detay penceresini çizen yardımcı fonksiyon
@st.dialog("📋 Sipariş Detay Kartı")
def siparis_detayini_goster(siparis_verisi):
    st.write(f"**🔢 Sipariş ID:** {siparis_verisi['Sipariş ID']}")
    st.write(f"**👤 Üye Adı Soyadı:** {siparis_verisi['Üye Adı Soyadı']} (No: {siparis_verisi['Üye No']})")
    st.write(f"**📦 Sipariş Edilen Ürün:** {siparis_verisi['Ürün']}")
    st.write(f"**🔢 Adet:** {siparis_verisi['Adet']}")
    st.write(f"**🚦 Güncel Durum:** {siparis_verisi['Durum']}")
    st.write(f"**📅 Kayıt Tarihi:** {siparis_verisi['Tarih']}")
    if pd.notna(siparis_verisi['Kargo Takip No']) and str(siparis_verisi['Kargo Takip No']).strip() != "":
        st.write(f"**🚚 Kargo No:** {siparis_verisi['Kargo Takip No']}")
    else:
        st.write("**🚚 Kargo No:** Henüz girilmemiş")

if not df_siparisler.empty:
    try:
        df_siparisler["Tarih_DT"] = pd.to_datetime(
            df_siparisler["Tarih"], errors="coerce"
        )
        bugun = pd.Timestamp(datetime.now().date())
        df_siparisler["Gecen_Gun"] = (bugun - df_siparisler["Tarih_DT"]).dt.days

        gecikmis_hazirlik = df_siparisler[
            (df_siparisler["Durum"] == "Hazırlanıyor")
            & (df_siparisler["Gecen_Gun"] >= 3)
        ]

        gecikmis_kargo = df_siparisler[
            (df_siparisler["Durum"] == "Yolda")
            & (df_siparisler["Gecen_Gun"] >= 5)
        ]

        if not gecikmis_hazirlik.empty or not gecikmis_kargo.empty:
            st.subheader("⚠️ Lojistik Aksiyon Gerekli!")

            col_alert1, col_alert2 = st.columns(2)

            with col_alert1:
                if not gecikmis_hazirlik.empty:
                    st.error(
                        f"🚨 **Hazırlık Gecikmesi ({len(gecikmis_hazirlik)} Sipariş):**\n"
                        f"En az **3 gündür** 'Hazırlanıyor' aşamasında bekleyen siparişler var! "
                        f"Detay için ID numarasına tıklayın:"
                    )
                    # Geciken ID'leri tıklanabilir butonlar halinde yan yana diziyoruz
                    cols_ids = st.columns(min(len(gecikmis_hazirlik), 6))
                    for idx, row in gecikmis_hazirlik.reset_index().iterrows():
                        col_target = cols_ids[idx % 6]
                        # Butona basıldığında yukarıdaki pop-up fonksiyonunu tetikliyoruz
                        if col_target.button(f"🆔 {row['Sipariş ID']}", key=f"haz_btn_{row['Sipariş ID']}"):
                            siparis_detayini_goster(row)

            with col_alert2:
                if not gecikmis_kargo.empty:
                    st.warning(
                        f"📦 **Kargo Teslimat Gecikmesi ({len(gecikmis_kargo)} Sipariş):**\n"
                        f"En az **5 gündür** 'Yolda' görünen ve teslim edilmeyen kargolar var! "
                        f"Detay için ID numarasına tıklayın:"
                    )
                    cols_ids_kargo = st.columns(min(len(gecikmis_kargo), 6))
                    for idx, row in gecikmis_kargo.reset_index().iterrows():
                        col_target = cols_ids_kargo[idx % 6]
                        if col_target.button(f"🆔 {row['Sipariş ID']}", key=f"krg_btn_{row['Sipariş ID']}"):
                            siparis_detayini_goster(row)

            st.markdown("---")
    except Exception as e:
        pass


# 6. ANA EKRAN - Filtrelenmiş Verileri Listeleme
st.subheader("📊 Üye Gönderim Listesi")

if not df_siparisler.empty:
    df_filtrelenmis = df_siparisler.copy()

    if ara_siparis_id:
        df_filtrelenmis = df_filtrelenmis[
            df_filtrelenmis["Sipariş ID"]
            .astype(str)
            .str.strip()
            .str.contains(ara_siparis_id, case=False, na=False)
        ]

    if ara_uye_no:
        df_filtrelenmis = df_filtrelenmis[
            df_filtrelenmis["Üye No"]
            .astype(str)
            .str.strip()
            .str.contains(ara_uye_no, case=False, na=False)
        ]

    if ara_uye_adi:
        df_filtrelenmis = df_filtrelenmis[
            df_filtrelenmis["Üye Adı Soyadı"]
            .astype(str)
            .str.strip()
            .str.contains(ara_uye_adi, case=False, na=False)
        ]

    if ara_urunler:
        df_filtrelenmis = df_filtrelenmis[
            df_filtrelenmis["Ürün"].isin(ara_urunler)
        ]

    if ara_durum != "Hepsi":
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis["Durum"] == ara_durum]

    ekran_df = df_filtrelenmis.drop(
        columns=["Tarih_DT", "Gecen_Gun"], errors="ignore"
    )
    st.dataframe(ekran_df, use_container_width=True)

    # EXCEL DIŞARI AKTAR BUTONU
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        ekran_df.to_excel(writer, index=False, sheet_name="Filtreli Liste")
    indirilecek_veri = buffer.getvalue()

    st.download_button(
        label="🟢 Listeyi Excel Olarak İndir (Filtreye Göre)",
        data=indirilecek_veri,
        file_name=f"filtrelenmis_uye_listesi_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # İstatistikler
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Listelenen Kayıt", len(df_filtrelenmis))
    col2.metric(
        "Teslim Edilenler",
        len(df_filtrelenmis[df_filtrelenmis["Durum"] == "Teslim Edildi"]),
    )
    col3.metric(
        "Toplam Ürün Adedi",
        int(df_filtrelenmis["Adet"].sum()) if not df_filtrelenmis.empty else 0,
    )
else:
    st.info("Henüz kaydedilmiş bir üye siparişi bulunmuyor.")

# 7. Toplu Veri Aktarım Alanı
st.markdown("---")
st.subheader("📥 Excel'den Toplu Veri Aktarımı")
yuklenen_dosya = st.file_uploader(
    "Sütunları 'Sipariş ID, Üye No, Üye Adı Soyadı, Ürün, Adet, Durum, Kargo Takip No, Tarih' olan Excel dosyasını seçin",
    type=["xlsx"],
)

if yuklenen_dosya is not None:
    try:
        df_yuklenen = pd.read_excel(yuklenen_dosya)
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
            st.error(f"Eksik sütunlar var: {', '.join(eksik_sutunlar)}")
        else:
            yontem = st.radio(
                "Aktarım Yöntemi:",
                ("Mevcut verilerin sonuna ekle", "Mevcut verileri sil, bunu kaydet"),
            )
            if st.button("Verileri Sisteme Aktar"):
                if yontem == "Mevcut verilerin sonuna ekle":
                    df_mevcut = verileri_getir()
                    df_son = pd.concat(
                        [df_mevcut, df_yuklenen], ignore_index=True
                    )
                    df_son.to_excel("siparisler.xlsx", index=False)
                else:
                    df_yuklenen.to_excel("siparisler.xlsx", index=False)
                st.success("Veriler başarıyla aktarıldı!")
                st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")
