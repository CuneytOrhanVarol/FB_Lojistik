import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ======================================================
# FB OPERASYON MERKEZİ - TEMİZ HAFİF SÜRÜM v1
# ======================================================

DB_NAME = "fb_operasyon_merkezi_v2.db"

KULLANICILAR = {
    "Cüneyt Orhan Varol": "fb01",
    "Mehmet Erkin Ataş": "fb02",
    "Ersen Avcı": "fb03",
    "Simay Önder": "fb04",
    "Pervin Hanım": "ipek123",
    "Mevlüt Bey": "ikba456",
    "Engin Bey": "kuker789"
}

YONETICILER = [
    "Cüneyt Orhan Varol",
    "Mehmet Erkin Ataş",
    "Ersen Avcı",
    "Simay Önder"
]

TEDARIKCI_DURUMLARI = {
    "Pervin Hanım": "Hazırlanıyor (İpek Kutu)",
    "Mevlüt Bey": "Hazırlanıyor (İkba Kristal)",
    "Engin Bey": "Hazırlanıyor (Kuker)"
}

DURUMLAR = [
    "Hazırlanıyor (Üye İlişkileri)",
    "Hazırlanıyor (Kuker)",
    "Hazırlanıyor (İkba Kristal)",
    "Hazırlanıyor (İpek Kutu)",
    "Kargoya verildi",
    "Teslim edildi"
]


# ======================================================
# YARDIMCI FONKSİYONLAR
# ======================================================

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


def yetki_bul(kullanici):
    if kullanici in YONETICILER:
        return "Yönetici"
    return "Tedarikçi"


# ======================================================
# BAŞLANGIÇ
# ======================================================

st.set_page_config(page_title="FB Operasyon Merkezi", layout="wide")
veritabani_hazirla()

# ======================================================
# GİRİŞ
# ======================================================

if "kullanici" not in st.session_state:
    st.title("🛡️ FB Operasyon Merkezi - Hafif Sürüm")

    kullanici_sec = st.selectbox("Kullanıcı", list(KULLANICILAR.keys()))
    sifre = st.text_input("Şifre", type="password")

    if st.button("Giriş Yap"):
        if KULLANICILAR.get(kullanici_sec) == sifre:
            st.session_state["kullanici"] = kullanici_sec
            st.session_state["yetki"] = yetki_bul(kullanici_sec)
            st.rerun()
        else:
            st.error("Hatalı şifre")

    st.stop()


mevcut_user = st.session_state["kullanici"]
yetki = st.session_state["yetki"]

st.sidebar.title(f"👤 {mevcut_user}")
st.sidebar.caption(f"Yetki: {yetki}")

menu = ["📦 Operasyon Paneli"]

if yetki == "Yönetici":
    menu.append("📂 Kayıt Ekle / Aktar")
    menu.append("🧹 Hatalı Kayıt Temizliği")
    menu.append("🕒 Log")

secim = st.sidebar.radio("Menü", menu)

# ======================================================
# OPERASYON PANELİ
# ======================================================

if secim == "📦 Operasyon Paneli":
    st.header("📦 Operasyon Paneli")
    st.info("Hafif mod: Listeleme en fazla 500 kayıt getirir.")

    col1, col2, col3 = st.columns([2, 1, 1])

    arama = col1.text_input("İsim / sicil / telefon ara")
    durum_filtre = col2.selectbox("Durum", ["Tümü"] + DURUMLAR)
   limit = col3.selectbox("Limit", [100, 300, 500, 1000, 5000], index=1)
sayfa = st.number_input("Sayfa No", min_value=1, value=1, step=1)
offset = (sayfa - 1) * limit

    query = """
        SELECT 
            id,
            sicil_no,
            uye_adi,
            telefon_no,
            urunler,
            adet,
            durum,
            kargo_no,
            kargo_tarihi,
            tarih,
            aktarim_id
        FROM siparisler
        WHERE silindi = 0
    """

    params = []

    if yetki == "Tedarikçi":
        query += " AND durum = ?"
        params.append(TEDARIKCI_DURUMLARI.get(mevcut_user))

    if arama:
        query += """
            AND (
                sicil_no LIKE ?
                OR uye_adi LIKE ?
                OR telefon_no LIKE ?
            )
        """
        params.extend([f"%{arama}%", f"%{arama}%", f"%{arama}%"])

    if durum_filtre != "Tümü":
        query += " AND durum = ?"
        params.append(durum_filtre)

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
params.append(limit)
params.append(offset)

    if st.button("Kayıtları Listele"):
        conn = baglan()
        df_liste = pd.read_sql_query(query, conn, params=params)
        conn.close()
        st.session_state["liste_df"] = df_liste

    if "liste_df" in st.session_state:
        df = st.session_state["liste_df"].copy()

        st.write(f"Listelenen kayıt sayısı: **{len(df)}**")

        if df.empty:
            st.warning("Kayıt bulunamadı.")
        else:
            df.insert(0, "Seç", False)

            edited_df = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Seç": st.column_config.CheckboxColumn("Seç"),
                    "id": None,
                    "kargo_no": st.column_config.TextColumn("Kargo No")
                },
                disabled=[
                    "sicil_no",
                    "uye_adi",
                    "telefon_no",
                    "urunler",
                    "adet",
                    "durum",
                    "kargo_tarihi",
                    "tarih",
                    "aktarim_id"
                ],
                key="editor_operasyon"
            )

            secilenler = edited_df[edited_df["Seç"] == True]

            if not secilenler.empty:
                st.subheader(f"Seçilen kayıt sayısı: {len(secilenler)}")

                yeni_durum = st.selectbox("Yeni durum", DURUMLAR)

                if st.button("Seçilenlerin Durumunu Güncelle"):
                    conn = baglan()
                    c = conn.cursor()

                    for _, row in secilenler.iterrows():
                        sid = int(row["id"])

                        if yeni_durum == "Kargoya verildi":
                            c.execute("""
                                UPDATE siparisler
                                SET durum = ?, kargo_tarihi = ?
                                WHERE id = ?
                            """, (yeni_durum, bugun(), sid))
                        else:
                            c.execute("""
                                UPDATE siparisler
                                SET durum = ?
                                WHERE id = ?
                            """, (yeni_durum, sid))

                    conn.commit()
                    conn.close()

                    log_ekle(mevcut_user, f"{len(secilenler)} kayıt '{yeni_durum}' yapıldı.")

                    del st.session_state["liste_df"]
                    st.success("Durum güncellendi.")
                    st.rerun()

# ======================================================
# KAYIT EKLE / AKTAR
# ======================================================

elif secim == "📂 Kayıt Ekle / Aktar":
    st.header("📂 Kayıt Ekle / Aktar")

    tab1, tab2 = st.tabs(["Manuel Ekle", "Excel Aktar"])

    with tab1:
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
                else:
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

    with tab2:
        dosya = st.file_uploader("Excel dosyası seç", type=["xlsx"])

        if dosya:
            df_raw = pd.read_excel(dosya, dtype=str)

            st.write("Excel ön izleme")
            st.dataframe(df_raw.head(20), use_container_width=True)

            kolonlar = ["Seçiniz"] + list(df_raw.columns)

            c1, c2, c3, c4 = st.columns(4)

            sicil_col = c1.selectbox("Sicil kolonu", kolonlar)
            ad_col = c2.selectbox("Ad Soyad kolonu", kolonlar)
            tel_col = c3.selectbox("Telefon kolonu", kolonlar)
            urun_col = c4.selectbox("Ürünler kolonu", kolonlar)

            if sicil_col != "Seçiniz" and ad_col != "Seçiniz" and urun_col != "Seçiniz":
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
                    else:
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

# ======================================================
# HATALI KAYIT TEMİZLİĞİ
# ======================================================

elif secim == "🧹 Hatalı Kayıt Temizliği":
    st.header("🧹 Hatalı Kayıt Temizliği")

    st.warning("Önce sayı kontrol et. Doğru sayı gelmeden silme yapma.")

    tarih_sec = st.text_input("Tarih", value=bugun())

    kriter = st.selectbox(
        "Silme kriteri",
        [
            "Sicil ve Ad Soyad boş olanlar",
            "Sicil boş olanlar",
            "Ad Soyad boş olanlar",
            "Aktarım ID olmayan + Sicil ve Ad Soyad boş olanlar",
            "Bu tarihteki tüm aktif kayıtlar"
        ]
    )

    extra = ""

    if kriter == "Sicil ve Ad Soyad boş olanlar":
        extra = f" AND {bos_sql('sicil_no')} AND {bos_sql('uye_adi')}"
    elif kriter == "Sicil boş olanlar":
        extra = f" AND {bos_sql('sicil_no')}"
    elif kriter == "Ad Soyad boş olanlar":
        extra = f" AND {bos_sql('uye_adi')}"
    elif kriter == "Aktarım ID olmayan + Sicil ve Ad Soyad boş olanlar":
        extra = f" AND {bos_sql('aktarim_id')} AND {bos_sql('sicil_no')} AND {bos_sql('uye_adi')}"
    elif kriter == "Bu tarihteki tüm aktif kayıtlar":
        extra = ""

    conn = baglan()

    count_query = f"""
        SELECT COUNT(*)
        FROM siparisler
        WHERE silindi = 0
        AND tarih = ?
        {extra}
    """

    adet = pd.read_sql_query(count_query, conn, params=[tarih_sec]).iloc[0, 0]

    st.metric("Etkilenecek kayıt sayısı", int(adet))

    preview_query = f"""
        SELECT id, sicil_no, uye_adi, telefon_no, urunler, durum, tarih, aktarim_id
        FROM siparisler
        WHERE silindi = 0
        AND tarih = ?
        {extra}
        ORDER BY id DESC
        LIMIT 100
    """

    df_preview = pd.read_sql_query(preview_query, conn, params=[tarih_sec])
    conn.close()

    st.write("İlk 100 kayıt")
    st.dataframe(df_preview, use_container_width=True)

    onay = st.checkbox("Bu kayıtları silmek istediğimi onaylıyorum.")
    metin = st.text_input("Devam etmek için SIL yaz")

    col1, col2 = st.columns(2)

    if col1.button("Arşivle / Sil"):
        if onay and metin == "SIL" and int(adet) > 0:
            conn = baglan()
            conn.execute(f"""
                UPDATE siparisler
                SET silindi = 1,
                    silinme_tarihi = ?
                WHERE silindi = 0
                AND tarih = ?
                {extra}
            """, (simdi(), tarih_sec))
            conn.commit()
            conn.close()

            log_ekle(mevcut_user, f"{adet} kayıt arşivlendi. Kriter: {kriter}")
            st.success(f"{adet} kayıt arşivlendi.")
            st.rerun()
        else:
            st.error("Onay kutusunu işaretle, SIL yaz ve sayı 0'dan büyük olsun.")

    if col2.button("Kalıcı Sil"):
        if onay and metin == "SIL" and int(adet) > 0:
            conn = baglan()
            conn.execute(f"""
                DELETE FROM siparisler
                WHERE silindi = 0
                AND tarih = ?
                {extra}
            """, (tarih_sec,))
            conn.commit()
            conn.close()

            log_ekle(mevcut_user, f"{adet} kayıt kalıcı silindi. Kriter: {kriter}")
            st.warning(f"{adet} kayıt kalıcı silindi.")
            st.rerun()
        else:
            st.error("Onay kutusunu işaretle, SIL yaz ve sayı 0'dan büyük olsun.")

# ======================================================
# LOG
# ======================================================

elif secim == "🕒 Log":
    st.header("🕒 Log")

    conn = baglan()
    df_log = pd.read_sql_query("""
        SELECT *
        FROM islem_gecmisi
        ORDER BY id DESC
        LIMIT 500
    """, conn)
    conn.close()

    st.dataframe(df_log, use_container_width=True)

# ======================================================
# ÇIKIŞ
# ======================================================

if st.sidebar.button("🚪 Çıkış"):
    st.session_state.clear()
    st.rerun()
