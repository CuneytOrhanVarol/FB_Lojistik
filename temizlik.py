import streamlit as st
import pandas as pd
from datetime import datetime
from database import baglan, bugun, temiz_str, log_ekle


def kayit_ekle_aktar(mevcut_user):
    st.header("📂 Kayıt Ekle / Aktar")

    tab1, tab2 = st.tabs(["Manuel Ekle", "Excel Aktar"])

    with tab1:
        manuel_ekle(mevcut_user)

    with tab2:
        excel_aktar(mevcut_user)


def manuel_ekle(mevcut_user):
    with st.form("manuel_form"):
        sicil = st.text_input("Sicil / Üye No")
        ad = st.text_input("Ad Soyad")
        telefon = st.text_input("Telefon")
        urunler = st.text_area("Ürünler")
        adet = st.number_input("Adet", min_value=1, value=1)

        kaydet = st.form_submit_button("Kaydet")

        if kaydet:
            if not sicil or not ad or not urunler:
                st.error("Sicil, Ad Soyad ve Ürünler boş olamaz.")
                return

            conn = baglan()
            conn.execute("""
                INSERT INTO siparisler
                (sicil_no, uye_adi, telefon_no, urunler, adet, durum, tarih, silindi)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                sicil,
                ad,
                telefon,
                urunler,
                adet,
                "Hazırlanıyor (Üye İlişkileri)",
                bugun()
            ))
            conn.commit()
            conn.close()

            log_ekle(mevcut_user, f"Manuel kayıt eklendi: {sicil} - {ad}")
            st.success("Kayıt eklendi.")


def excel_aktar(mevcut_user):
    dosya = st.file_uploader("Excel dosyası seç", type=["xlsx"])

    if not dosya:
        return

    df_raw = pd.read_excel(dosya, dtype=str)

    st.write("Excel ön izleme")
    st.dataframe(df_raw.head(20), use_container_width=True)

    kolonlar = ["Seçiniz"] + list(df_raw.columns)

    c1, c2, c3, c4 = st.columns(4)

    sicil_col = c1.selectbox("Sicil kolonu", kolonlar)
    ad_col = c2.selectbox("Ad Soyad kolonu", kolonlar)
    tel_col = c3.selectbox("Telefon kolonu", kolonlar)
    urun_col = c4.selectbox("Ürünler kolonu", kolonlar)

    if sicil_col == "Seçiniz" or ad_col == "Seçiniz" or urun_col == "Seçiniz":
        st.warning("Sicil, Ad Soyad ve Ürünler kolonlarını seçmelisin.")
        return

    df_imp = pd.DataFrame()
    df_imp["sicil_no"] = df_raw[sicil_col].apply(temiz_str)
    df_imp["uye_adi"] = df_raw[ad_col].apply(temiz_str)
    df_imp["telefon_no"] = df_raw[tel_col].apply(temiz_str) if tel_col != "Seçiniz" else ""
    df_imp["urunler"] = df_raw[urun_col].apply(temiz_str)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Toplam Satır", len(df_imp))
    k2.metric("Boş Sicil", int((df_imp["sicil_no"] == "").sum()))
    k3.metric("Boş Ad Soyad", int((df_imp["uye_adi"] == "").sum()))
    k4.metric("Boş Ürün", int((df_imp["urunler"] == "").sum()))

    st.write("Aktarım ön izleme")
    st.dataframe(df_imp.head(20), use_container_width=True)

    onay = st.checkbox("Kontrol ettim, aktarımı başlat.")

    if st.button("Excel'i Aktar"):
        if not onay:
            st.error("Önce onay kutusunu işaretle.")
            return

        aktarim_id = datetime.now().strftime("AKT-%Y%m%d-%H%M%S")

        eklenen = 0
        atlanan = 0

        conn = baglan()
        c = conn.cursor()

        for _, r in df_imp.iterrows():
            sicil = temiz_str(r["sicil_no"])
            ad = temiz_str(r["uye_adi"])
            telefon = temiz_str(r["telefon_no"])
            urun = temiz_str(r["urunler"])

            if sicil == "" or ad == "" or urun == "":
                atlanan += 1
                continue

            c.execute("""
                INSERT INTO siparisler
                (sicil_no, uye_adi, telefon_no, urunler, adet, durum, tarih, aktarim_id, silindi)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?, 0)
            """, (
                sicil,
                ad,
                telefon,
                urun,
                "Hazırlanıyor (Üye İlişkileri)",
                bugun(),
                aktarim_id
            ))

            eklenen += 1

        conn.commit()
        conn.close()

        log_ekle(
            mevcut_user,
            f"Excel aktarımı yapıldı. Aktarım ID: {aktarim_id}, Eklenen: {eklenen}, Atlanan: {atlanan}"
        )

        st.success(f"Aktarım tamamlandı. Aktarım ID: {aktarim_id} | Eklenen: {eklenen} | Atlanan: {atlanan}")
