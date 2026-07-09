
import sqlite3
from datetime import datetime
import pandas as pd

DB_NAME = "fb_operasyon_merkezi_v2.db"


def baglan():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def simdi():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def bugun():
    return datetime.now().strftime("%d/%m/%Y")


def temiz_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def bos_sql(kolon):
    return f"""
    (
        {kolon} IS NULL
        OR TRIM({kolon}) = ''
        OR LOWER(TRIM({kolon})) = 'nan'
        OR LOWER(TRIM({kolon})) = 'none'
        OR LOWER(TRIM({kolon})) = 'null'
    )
    """


def kolon_ekle(conn, tablo, kolon, tip):
    try:
        conn.execute(f"ALTER TABLE {tablo} ADD COLUMN {kolon} {tip}")
        conn.commit()
    except sqlite3.OperationalError:
        pass


def veritabani_hazirla():
    conn = baglan()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS siparisler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sicil_no TEXT,
        uye_adi TEXT,
        telefon_no TEXT,
        urunler TEXT,
        adet INTEGER DEFAULT 1,
        durum TEXT,
        kargo_no TEXT,
        kargo_tarihi TEXT,
        tarih TEXT,
        birim_maliyet REAL DEFAULT 0.0,
        odeme_durumu TEXT DEFAULT 'Bekliyor',
        aktarim_id TEXT,
        silindi INTEGER DEFAULT 0,
        silinme_tarihi TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS islem_gecmisi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici TEXT,
        islem TEXT,
        zaman TEXT
    )
    """)

    conn.commit()

    kolon_ekle(conn, "siparisler", "aktarim_id", "TEXT")
    kolon_ekle(conn, "siparisler", "silindi", "INTEGER DEFAULT 0")
    kolon_ekle(conn, "siparisler", "silinme_tarihi", "TEXT")

    conn.execute("UPDATE siparisler SET silindi = 0 WHERE silindi IS NULL")
    conn.commit()
    conn.close()


def log_ekle(kullanici, islem):
    conn = baglan()
    conn.execute(
        "INSERT INTO islem_gecmisi (kullanici, islem, zaman) VALUES (?, ?, ?)",
        (kullanici, islem, simdi())
    )
    conn.commit()
    conn.close()
