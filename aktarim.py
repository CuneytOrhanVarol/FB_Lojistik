def siparis_durum_guncelle(siparis_id, yeni_durum, yeni_kargo_no=None):
    """Belirtilen Sipariş ID'sine sahip kaydın durumunu ve kargo numarasını günceller."""
    excel_kontrol_et()
    df = pd.read_excel(EXCEL_FILE)

    # Sipariş ID sütununu metne çevirip arıyoruz (tür uyuşmazlığı olmasın diye)
    siparis_id_str = str(siparis_id).strip()
    df_id_str = df["Sipariş ID"].astype(str).str.strip()

    # İlgili siparişin indeksini bul
    indeksler = df[df_id_str == siparis_id_str].index

    if not indeksler.empty:
        # Durumu güncelle
        df.loc[indeksler, "Durum"] = yeni_durum

        # Eğer kargo numarası girildiyse ve boş değilse kargo numarasını da güncelle
        if yeni_kargo_no and str(yeni_kargo_no).strip() != "":
            df.loc[indeksler, "Kargo Takip No"] = yeni_kargo_no.strip()

        # Değişiklikleri kaydet
        df.to_excel(EXCEL_FILE, index=False)
        return True
    return False
