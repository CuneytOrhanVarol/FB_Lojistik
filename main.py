# Ana Ekranın En Altına - Toplu Veri Aktarım Alanı
st.markdown("---")
st.subheader("📥 Excel'den Toplu Veri Aktarımı")
st.write(
    "Elinizdeki mevcut Excel dosyasını yükleyerek sisteme toplu aktarım yapabilirsiniz."
)

# Dosya yükleme bileşeni
yuklenen_dosya = st.file_uploader(
    "Sütunları 'Sipariş ID, Üye No, Üye Adı Soyadı, Ürün, Adet, Durum, Tarih' olan Excel dosyasını seçin",
    type=["xlsx"],
)

if yuklenen_dosya is not None:
    try:
        # Yüklenen Excel dosyasını Pandas ile oku
        df_yuklenen = pd.read_excel(yuklenen_dosya)

        # Gerekli sütunların kontrolü
        gerekli_sutunlar = [
            "Sipariş ID",
            "Üye No",
            "Üye Adı Soyadı",
            "Ürün",
            "Adet",
            "Durum",
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

            # İki farklı aktarım seçeneği sunalım
            yontem = st.radio(
                "Aktarım Yöntemi Seçin:",
                (
                    "Mevcut verilerin sonuna ekle (Üzerine yazma)",
                    "Mevcut verileri sil, sadece bu dosyayı kaydet",
                ),
            )

            aktar_butonu = st.button("Verileri Sisteme Aktar")

            if aktar_butonu:
                if (
                    yontem == "Mevcut verilerin sonuna ekle (Üzerine yazma)"
                ):  # Düzeltme: "Sonuna ekle" mantığı
                    df_mevcut = verileri_getir()
                    df_son = pd.concat(
                        [df_mevcut, df_yuklenen], ignore_index=True
                    )
                    df_son.to_excel("siparisler.xlsx", index=False)
                else:
                    df_yuklenen.to_excel("siparisler.xlsx", index=False)

                st.success(
                    "🎉 Veriler başarıyla aktarıldı! Sayfayı yenilemek için F5 yapabilir veya menüyü kullanabilirsiniz."
                )
                # Tablonun anında güncellenmesi için Streamlit'i yeniden çalıştırır
                st.rerun()

    except Exception as e:
        st.error(f"Dosya okunurken bir hata oluştu: {e}")
