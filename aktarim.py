import os
import pandas as pd

EXCEL_FILE = "siparisler.xlsx"


def excel_kontrol_et():
    """Excel dosyası yoksa kargo takipli şablon olarak oluşturur."""
    if not os.path.exists(EXCEL_FILE):
        df = pd.DataFrame(
            columns=[
                "Sipariş ID",
                "Üye No",
                "Üye Adı Soyadı",
                "Ürün",
                "Adet",
                "Durum",
                "Kargo Takip No",  # Yeni eklenen sütun
                "Tarih",
            ]
        )
        df.to_excel(EXCEL_FILE, index=False)


def kayit_ekle_aktar(
    siparis_id, uye_no, uye_adi, urun, adet, durum, kargo_no, tarih
):
    """Yeni üye siparişini kargo bilgisiyle birlikte Excel'e ekler."""
    excel_kontrol_et()

    # Mevcut verileri oku
    df = pd.read_excel(EXCEL_FILE)

    # Yeni sipariş satırı
    yeni_satir = pd.DataFrame(
        [
            {
                "Sipariş ID": siparis_id,
                "Üye No": uye_no,
                "Üye Adı Soyadı": uye_adi,
                "Ürün": urun,
                "Adet": adet,
                "Durum": durum,
                "Kargo Takip No": kargo_no,  # Yeni eklenen alan
                "Tarih": tarih,
            }
        ]
    )

    # Verileri birleştir ve kaydet
    df = pd.concat([df, yeni_satir], ignore_index=True)
    df.to_excel(EXCEL_FILE, index=False)


def verileri_getir():
    """Tüm üye siparişlerini DataFrame olarak döner."""
    excel_kontrol_et()
    return pd.read_excel(EXCEL_FILE)
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
