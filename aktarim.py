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
