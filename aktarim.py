import os
import pandas as pd

EXCEL_FILE = "siparisler.xlsx"


def excel_kontrol_et():
    """Excel dosyası yoksa üyelik sistemine uygun şablon olarak oluşturur."""
    if not os.path.exists(EXCEL_FILE):
        df = pd.DataFrame(
            columns=[
                "Sipariş ID",
                "Üye No",
                "Üye Adı Soyadı",
                "Ürün",
                "Adet",
                "Durum",
                "Tarih",
            ]
        )
        df.to_excel(EXCEL_FILE, index=False)


def kayit_ekle_aktar(siparis_id, uye_no, uye_adi, urun, adet, durum, tarih):
    """Yeni üye siparişini Excel dosyasına ekler."""
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
