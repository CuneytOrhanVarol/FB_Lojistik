import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ======================================================
# FB OPERASYON MERKEZİ - HAFİF SÜRÜM v7.2
# ======================================================

DB_NAME = "fb_operasyon_merkezi_v2.db"

conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

# ------------------------------------------------------
# AYARLAR
# ------------------------------------------------------

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

# ------------------------------------------------------
# VERİTABANI
# ------------------------------------------------------

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


def kolon_ekle(tablo, kolon, tip):
    try:
        c.execute(f"ALTER TABLE {tablo} ADD COLUMN {kolon} {tip}")
        conn.commit()
    except sqlite3.OperationalError:
        pass


kolon_ekle("siparisler", "aktarim_id", "TEXT")
kolon_ekle("siparisler", "silindi", "INTEGER DEFAULT 0")
kolon_ekle("siparisler", "silinme_tarihi", "TEXT")

c.execute("UPDATE siparisler SET silindi = 0 WHERE silindi IS NULL")
conn.commit()

# ------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ------------------------------------------------------

def simdi():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def bugun():
    return datetime.now().strftime("%d/%m/%Y")


def temiz_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def log_ekle(kullanici, islem):
    c.execute(
        "INSERT INTO islem_gecmisi (kullanici, islem, zaman) VALUES (?, ?, ?)",
        (kullanici, islem, simdi())
    )
    conn.commit()


def yetki_bul(kullanici):
    return "Yönetici" if kullanici in YONETICILER else "Tedarikçi"


def bos_deger_sql(kolon):
    return f"""
    (
        {kolon} IS NULL
        OR TRIM({kolon}) = ''
        OR LOWER(TRIM({kolon})) = 'nan'
        OR LOWER(TRIM({kolon})) = 'none'
        OR LOWER(TRIM({kolon})) = 'null'
    )
    """


def durum_guncelle(siparis_id, yeni_durum, kullanici):
    if yeni_durum == "Kargoya verildi":
        c.execute("""
            UPDATE siparisler
            SET durum = ?, kargo_tarihi = ?
            WHERE id = ?
        """, (yeni_durum, bugun(), siparis_id))
    else:
        c.execute("""
            UPDATE siparisler
            SET durum = ?
            WHERE id = ?
        """, (yeni_durum, siparis_id))

    conn.commit()
    log_ekle(kullanici, f"ID {siparis_id} durumu '{yeni_durum}' yapıldı.")


# ------------------------------------------------------
# SAYFA
# ------------------------------------------------------

st.set_page_config(page_title="FB Operasyon Merkezi v7.2", layout="wide")

# ------------------------------------------------------
# GİRİŞ
# ------------------------------------------------------

if "kullanici" not in st.session_state:
    st.title("🛡️ FB Operasyon Merkezi v7.2 - Hafif Sürüm")

    user = st.selectbox("Kullanıcı Seçin", list(KULLANICILAR.keys()))
    sifre = st.text_input("Şifre", type="password")

    if st.button("Sisteme Giriş Yap"):
        if KULLANICILAR.get(user) == sifre:
            st.session_state["kullanici"] = user
            st.session_state["yetki"] = yetki_bul(user)
            st.rerun()
        else:
            st.error("Hatalı şifre!")

else:
    mevcut_user = st.session_state["kullanici"]
    yetki = st.session_state["yetki"]

    st.sidebar.title(f"👤 {mevcut_user}")
    st.sidebar.caption(f"Yetki: {yetki}")

    menu = ["📦 Operasyon Paneli"]

    if yetki == "Yönetici":
        menu += ["📂 Kayıt Ekle / Aktar", "🧹 Hatalı Kayıt Temizliği", "🕒 Log"]

    secim = st.sidebar.radio("Menü", menu)

    # ==================================================
    # OPERASYON PANELİ
    # ==================================================

    if secim == "📦 Operasyon Paneli":
        st.header("📦 Operasyon Paneli")

        st.info("Sistem hafif modda çalışıyor. En fazla 500 kayıt listelenir.")

        col1, col2, col3 = st.columns([2, 1, 1])

        arama = col1.text_input("İsim, sicil veya telefon ara")
        durum_filtre = col2.selectbox("Durum", ["Tümü"] + DURUMLAR)
        limit = col3.selectbox("Liste limiti", [100, 300, 500], index=1)

        query = """
            SELECT id, sicil_no, uye_adi, telefon_no, urunler, adet, durum, kargo_no, kargo_tarihi, tarih, aktarim_id
            FROM siparisler
            WHERE silindi = 0
        """
        params = []

        if yetki == "Tedarikçi":
            tedarikci_durum = TEDARIKCI_DURUMLARI.get(mevcut_user)
            query += " AND durum = ?"
            params.append(tedarikci_durum)

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

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        if st.button("Kayıtları Listele"):
            df = pd.read_sql_query(query, conn, params=params)

            st.session_state["op_df"] = df

        if "op_df" in st.session_state:
            df = st.session_state["op_df"]

            st.write(f"Listelenen kayıt sayısı: **{len(df)}**")

            if df.empty:
                st.warning("Kayıt bulunamadı.")
            else:
                df.insert(0, "Seç", False)

                edited_df = st.data_editor(
                    df,
                    column_config={
                        "Seç": st.column_config.CheckboxColumn("Seç"),
                        "id": None,
                        "kargo_no": "Kargo No"
                    },
                    disabled=[
                        "id",
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
                    use_container_width=True,
                    hide_index=True,
                    key="op_editor"
                )

                selected_ids = edited_df[edited_df["Seç"] == True]["id"].tolist()

                if selected_ids:
                    st.subheader(f"Seçilen kayıt: {len(selected_ids)}")

                    yeni_durum = st.selectbox("Yeni durum seç", DURUMLAR)

                    if st.button("Seçilenlerin Durumunu Güncelle"):
                        for sid in selected_ids:
                            durum_guncelle(int(sid), yeni_durum, mevcut_user)

                        st.success(f"{len(selected_ids)} kayıt güncellendi.")
                        del st.session_state["op_df"]
                        st.rerun()

    # ==================================================
    # KAYIT EKLE / AKTAR
    # ==================================================

    elif secim == "📂 Kayıt Ekle / Aktar":
        st.header("📂 Kayıt Ekle / Aktar")

        t1, t2 = st.tabs(["Manuel Ekle", "Excel Aktar"])

        with t1:
            with st.form("manuel_form"):
                sicil = st.text_input("Sicil / Üye No")
                ad = st.text_input("Ad Soyad")
                tel = st.text_input("Telefon")
                urun = st.text_area("Ürünler")
                adet = st.number_input("Adet", min_value=1, value=1)

                if st.form_submit_button("Kaydet"):
                    if not sicil or not ad or not urun:
                        st.error("Sicil, Ad Soyad ve Ürünler boş olamaz.")
                    else:
                        c.execute("""
                            INSERT INTO siparisler
                            (sicil_no, uye_adi, telefon_no, urunler, adet, durum, tarih, silindi)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                        """, (
                            sicil,
                            ad,
                            tel,
                            urun,
                            adet,
                            "Hazırlanıyor (Üye İlişkileri)",
                            bugun()
                        ))

                        conn.commit()
                        log_ekle(mevcut_user, f"Manuel kayıt eklendi: {sicil} - {ad}")
                        st.success("Kayıt eklendi.")
                        st.rerun()

        with t2:
            up = st.file_uploader("Excel seç", type=["xlsx"])

            if up:
                df_raw = pd.read_excel(up, dtype=str)

                st.write("Ön izleme")
                st.dataframe(df_raw.head(20), use_container_width=True)

                excel_cols = ["Seçiniz"] + list(df_raw.columns)

                c1, c2, c3, c4 = st.columns(4)

                sicil_col = c1.selectbox("Sicil kolonu", excel_cols)
                ad_col = c2.selectbox("Ad Soyad kolonu", excel_cols)
                tel_col = c3.selectbox("Telefon kolonu", excel_cols)
                urun_col = c4.selectbox("Ürünler kolonu", excel_cols)

                if sicil_col != "Seçiniz" and ad_col != "Seçiniz" and urun_col != "Seçiniz":
                    df_imp = pd.DataFrame()
                    df_imp["sicil_no"] = df_raw[sicil_col].apply(temiz_str)
                    df_imp["uye_adi"] = df_raw[ad_col].apply(temiz_str)
                    df_imp["telefon_no"] = df_raw[tel_col].apply(temiz_str) if tel_col != "Seçiniz" else ""
                    df_imp["urunler"] = df_raw[urun_col].apply(temiz_str)

                    bos_sicil = (df_imp["sicil_no"] == "").sum()
                    bos_ad = (df_imp["uye_adi"] == "").sum()
                    bos_urun = (df_imp["urunler"] == "").sum()

                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Toplam Satır", len(df_imp))
                    k2.metric("Boş Sicil", int(bos_sicil))
                    k3.metric("Boş Ad Soyad", int(bos_ad))
                    k4.metric("Boş Ürün", int(bos_urun))

                    st.dataframe(df_imp.head(20), use_container_width=True)

                    onay = st.checkbox("Kontrol ettim, aktarımı başlatmak istiyorum.")

                    if st.button("Aktar"):
                        if not onay:
                            st.error("Aktarım için onay kutusunu işaretle.")
                        else:
                            aktarim_id = datetime.now().strftime("AKT-%Y%m%d-%H%M%S")

                            eklenen = 0
                            atlanan = 0

                            for _, r in df_imp.iterrows():
                                sicil = temiz_str(r["sicil_no"])
                                ad = temiz_str(r["uye_adi"])
                                tel = temiz_str(r["telefon_no"])
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
                                    tel,
                                    urun,
                                    "Hazırlanıyor (Üye İlişkileri)",
                                    bugun(),
                                    aktarim_id
                                ))

                                eklenen += 1

                            conn.commit()

                            log_ekle(
                                mevcut_user,
                                f"Excel aktarımı yapıldı. Aktarım ID: {aktarim_id}, Eklenen: {eklenen}, Atlanan: {atlanan}"
                            )

                            st.success(
                                f"Aktarım tamamlandı. Aktarım ID: {aktarim_id} | Eklenen: {eklenen} | Atlanan: {atlanan}"
                            )

                            st.rerun()

    # ==================================================
    # HATALI KAYIT TEMİZLİĞİ
    # ==================================================

    elif secim == "🧹 Hatalı Kayıt Temizliği":
        st.header("🧹 Hatalı Kayıt Temizliği")

        st.warning("Bu alan büyük hatalı yüklemeleri temizlemek içindir. Önce sayı kontrol et.")

        tarih_sec = st.text_input("Tarih", value=bugun())

        kriter = st.selectbox(
            "Kriter",
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
            extra = f" AND {bos_deger_sql('sicil_no')} AND {bos_deger_sql('uye_adi')}"
        elif kriter == "Sicil boş olanlar":
            extra = f" AND {bos_deger_sql('sicil_no')}"
        elif kriter == "Ad Soyad boş olanlar":
            extra = f" AND {bos_deger_sql('uye_adi')}"
        elif kriter == "Aktarım ID olmayan + Sicil ve Ad Soyad boş olanlar":
            extra = f"""
                AND {bos_deger_sql('aktarim_id')}
                AND {bos_deger_sql('sicil_no')}
                AND {bos_deger_sql('uye_adi')}
            """
        elif kriter == "Bu tarihteki tüm aktif kayıtlar":
            extra = ""

        count_query = f"""
            SELECT COUNT(*)
            FROM siparisler
            WHERE silindi = 0
            AND tarih = ?
            {extra}
        """

        c.execute(count_query, (tarih_sec,))
        adet = c.fetchone()[0]

        st.metric("Etkilenecek kayıt sayısı", adet)

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

        st.write("İlk 100 kayıt ön izleme")
        st.dataframe(df_preview, use_container_width=True)

        onay = st.checkbox("Bu kayıtları silmek istediğimi onaylıyorum.")
        metin = st.text_input("Devam etmek için SIL yaz")

        col1, col2 = st.columns(2)

        if col1.button("Arşivle / Sil"):
            if onay and metin == "SIL" and adet > 0:
                update_query = f"""
                    UPDATE siparisler
                    SET silindi = 1,
                        silinme_tarihi = ?
                    WHERE silindi = 0
                    AND tarih = ?
                    {extra}
                """

                c.execute(update_query, (simdi(), tarih_sec))
                conn.commit()

                log_ekle(
                    mevcut_user,
                    f"Hatalı kayıtlar arşivlendi. Tarih: {tarih_sec}, Kriter: {kriter}, Adet: {adet}"
                )

                st.success(f"{adet} kayıt arşivlendi.")
                st.rerun()
            else:
                st.error("Onay kutusunu işaretle, SIL yaz ve kayıt sayısının 0'dan büyük olduğundan emin ol.")

        if col2.button("Kalıcı Sil"):
            if onay and metin == "SIL" and adet > 0:
                delete_query = f"""
                    DELETE FROM siparisler
                    WHERE silindi = 0
                    AND tarih = ?
                    {extra}
                """

                c.execute(delete_query, (tarih_sec,))
                conn.commit()

                log_ekle(
                    mevcut_user,
                    f"Hatalı kayıtlar kalıcı silindi. Tarih: {tarih_sec}, Kriter: {kriter}, Adet: {adet}"
                )

                st.warning(f"{adet} kayıt kalıcı silindi.")
                st.rerun()
            else:
                st.error("Onay kutusunu işaretle, SIL yaz ve kayıt sayısının 0'dan büyük olduğundan emin ol.")

    # ==================================================
    # LOG
    # ==================================================

    elif secim == "🕒 Log":
        st.header("🕒 Log")

        df_log = pd.read_sql_query("""
            SELECT *
            FROM islem_gecmisi
            ORDER BY id DESC
            LIMIT 500
        """, conn)

        st.dataframe(df_log, use_container_width=True)

    # --------------------------------------------------
    # ÇIKIŞ
    # --------------------------------------------------

    if st.sidebar.button("🚪 Çıkış"):
        del st.session_state["kullanici"]
        del st.session_state["yetki"]
        st.rerun()
