import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px

# ======================================================
# FB OPERASYON MERKEZİ v7.0
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

c.execute("""
CREATE TABLE IF NOT EXISTS durum_gecmisi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    siparis_id INTEGER,
    eski_durum TEXT,
    yeni_durum TEXT,
    kullanici TEXT,
    zaman TEXT
)
""")

conn.commit()


def kolon_ekle(tablo, kolon, tip):
    """Eski veritabanlarında eksik kolon varsa ekler."""
    try:
        c.execute(f"ALTER TABLE {tablo} ADD COLUMN {kolon} {tip}")
        conn.commit()
    except sqlite3.OperationalError:
        pass


# Eski DB kullananlar için garanti kolon ekleme
kolon_ekle("siparisler", "aktarim_id", "TEXT")
kolon_ekle("siparisler", "silindi", "INTEGER DEFAULT 0")
kolon_ekle("siparisler", "silinme_tarihi", "TEXT")


# ------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ------------------------------------------------------

def simdi():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def bugun():
    return datetime.now().strftime("%d/%m/%Y")


def log_ekle(kullanici, islem):
    c.execute(
        "INSERT INTO islem_gecmisi (kullanici, islem, zaman) VALUES (?, ?, ?)",
        (kullanici, islem, simdi())
    )
    conn.commit()


def durum_log_ekle(siparis_id, eski_durum, yeni_durum, kullanici):
    c.execute("""
        INSERT INTO durum_gecmisi 
        (siparis_id, eski_durum, yeni_durum, kullanici, zaman)
        VALUES (?, ?, ?, ?, ?)
    """, (siparis_id, eski_durum, yeni_durum, kullanici, simdi()))
    conn.commit()


def kullanici_yetkisi(kullanici):
    return "Yönetici" if kullanici in YONETICILER else "Tedarikçi"


def kullanici_where(kullanici):
    """
    Yönetici tüm aktif kayıtları görür.
    Tedarikçi sadece kendi durumundaki aktif kayıtları görür.
    """
    if kullanici in YONETICILER:
        return "WHERE silindi = 0", []

    durum = TEDARIKCI_DURUMLARI.get(kullanici)
    return "WHERE silindi = 0 AND durum = ?", [durum]


def siparisleri_getir(kullanici, ekstra_where="", params=None):
    if params is None:
        params = []

    base_where, base_params = kullanici_where(kullanici)
    query = f"SELECT * FROM siparisler {base_where}"

    if ekstra_where:
        query += " " + ekstra_where
        base_params.extend(params)

    query += " ORDER BY id DESC"
    return pd.read_sql_query(query, conn, params=base_params)


def durum_guncelle(siparis_id, yeni_durum, kullanici):
    c.execute("SELECT durum FROM siparisler WHERE id = ?", (siparis_id,))
    row = c.fetchone()

    if not row:
        return

    eski_durum = row[0]

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
    durum_log_ekle(siparis_id, eski_durum, yeni_durum, kullanici)


def kaydi_arsivle(siparis_id, kullanici):
    c.execute("""
        UPDATE siparisler
        SET silindi = 1, silinme_tarihi = ?
        WHERE id = ?
    """, (simdi(), siparis_id))
    conn.commit()
    log_ekle(kullanici, f"ID {siparis_id} arşivlendi/silindi.")


def kaydi_kalici_sil(siparis_id, kullanici):
    c.execute("DELETE FROM siparisler WHERE id = ?", (siparis_id,))
    conn.commit()
    log_ekle(kullanici, f"ID {siparis_id} kalıcı olarak silindi.")


# ------------------------------------------------------
# SAYFA
# ------------------------------------------------------

st.set_page_config(page_title="FB Operasyon Merkezi v7.0", layout="wide")

# ------------------------------------------------------
# GİRİŞ
# ------------------------------------------------------

if "kullanici" not in st.session_state:
    st.title("🛡️ FB Operasyon Merkezi v7.0")

    user = st.selectbox("Kullanıcı Seçin", list(KULLANICILAR.keys()))
    sifre = st.text_input("Şifre", type="password")

    if st.button("Sisteme Giriş Yap"):
        if KULLANICILAR.get(user) == sifre:
            st.session_state["kullanici"] = user
            st.session_state["yetki"] = kullanici_yetkisi(user)
            st.rerun()
        else:
            st.error("Hatalı şifre!")

# ------------------------------------------------------
# ANA UYGULAMA
# ------------------------------------------------------

else:
    mevcut_user = st.session_state["kullanici"]
    yetki = st.session_state["yetki"]

    st.sidebar.title(f"👤 {mevcut_user}")
    st.sidebar.caption(f"Yetki: {yetki}")

    menu = [
        "📦 Operasyon Paneli",
        "📈 Performans & Finans",
        "📂 Kayıt Ekle / Aktar",
        "🗑️ Yönetim",
        "🕒 Log"
    ]

    secim = st.sidebar.radio("Menü", menu)

    # ==================================================
    # OPERASYON PANELİ
    # ==================================================

    if secim == "📦 Operasyon Paneli":
        st.header("🚀 Operasyonel Akış Kontrolü")

        df_all = siparisleri_getir(mevcut_user)

        if df_all.empty:
            st.info("Görüntülenecek aktif kayıt yok.")
        else:
            c1, c2, c3, c4 = st.columns(4)

            c1.metric("Toplam Aktif", len(df_all))
            c2.metric(
                "Üye İlişkileri",
                len(df_all[df_all["durum"] == "Hazırlanıyor (Üye İlişkileri)"])
            )
            c3.metric(
                "Tedarikçi Hazırlık",
                len(df_all[df_all["durum"].str.contains("Hazırlanıyor", na=False)])
            )
            c4.metric(
                "Kargo/Teslim",
                len(df_all[df_all["durum"].isin(["Kargoya verildi", "Teslim edildi"])])
            )

            st.divider()

            col_a, col_b = st.columns([2, 1])

            s_query = col_a.text_input("🔍 Hızlı Bul - İsim, Sicil veya Telefon")
            s_status = col_b.selectbox("Durum Filtresi", ["Tümü"] + DURUMLAR)

            ekstra = ""
            params = []

            if s_query:
                ekstra += " AND (uye_adi LIKE ? OR sicil_no LIKE ? OR telefon_no LIKE ?)"
                params.extend([f"%{s_query}%"] * 3)

            if s_status != "Tümü":
                ekstra += " AND durum = ?"
                params.append(s_status)

            df = siparisleri_getir(mevcut_user, ekstra, params)

            if df.empty:
                st.warning("Aranan kriterlerde kayıt bulunamadı.")
            else:
                st.write("### 📝 İşlem Bekleyen Kayıtlar")

                df.insert(0, "Seç", False)

                edited_df = st.data_editor(
                    df,
                    column_config={
                        "Seç": st.column_config.CheckboxColumn("Seç", default=False),
                        "id": None,
                        "birim_maliyet": None,
                        "silindi": None,
                        "silinme_tarihi": None,
                        "kargo_no": "Kargo No",
                        "kargo_tarihi": "Kargo Tarihi",
                        "aktarim_id": "Aktarım ID"
                    },
                    disabled=[
                        "id",
                        "sicil_no",
                        "uye_adi",
                        "telefon_no",
                        "urunler",
                        "adet",
                        "durum",
                        "tarih",
                        "kargo_tarihi",
                        "aktarim_id",
                        "odeme_durumu"
                    ],
                    use_container_width=True,
                    hide_index=True,
                    key="op_editor"
                )

                selected_ids = edited_df[edited_df["Seç"] == True]["id"].tolist()

                if selected_ids:
                    st.subheader(f"⚡ Seçilen {len(selected_ids)} kayıt için işlem")

                    btn_cols = st.columns(len(DURUMLAR))

                    for i, d_adi in enumerate(DURUMLAR):
                        label = d_adi.split("(")[-1].replace(")", "") if "(" in d_adi else d_adi

                        if btn_cols[i].button(label, key=f"durum_btn_{i}"):
                            for sid in selected_ids:
                                durum_guncelle(sid, d_adi, mevcut_user)

                            log_ekle(
                                mevcut_user,
                                f"{len(selected_ids)} kayıt '{d_adi}' durumuna alındı."
                            )
                            st.success("Durum güncellemesi tamamlandı.")
                            st.rerun()

    # ==================================================
    # PERFORMANS & FİNANS
    # ==================================================

    elif secim == "📈 Performans & Finans":
        st.header("📈 Analitik Özet")

        df_p = siparisleri_getir(mevcut_user)

        if df_p.empty:
            st.info("Analiz için kayıt yok.")
        else:
            k1, k2, k3 = st.columns(3)

            k1.metric("Aktif Kayıt", len(df_p))
            k2.metric("Toplam Maliyet", f"{df_p['birim_maliyet'].fillna(0).sum():,.2f} TL")
            k3.metric("Teslim Edilen", len(df_p[df_p["durum"] == "Teslim edildi"]))

            col_g1, col_g2 = st.columns(2)

            durum_ozet = df_p.groupby("durum").size().reset_index(name="Sayı")
            fig_bar = px.bar(
                durum_ozet,
                x="durum",
                y="Sayı",
                color="durum",
                title="Durum Bazlı Yük Dağılımı"
            )
            col_g1.plotly_chart(fig_bar, use_container_width=True)

            df_p["tarih_dt"] = pd.to_datetime(df_p["tarih"], dayfirst=True, errors="coerce")
            daily = df_p.groupby("tarih_dt").size().reset_index(name="Adet")

            fig_line = px.line(
                daily,
                x="tarih_dt",
                y="Adet",
                markers=True,
                title="Kayıt Giriş Trendi"
            )
            col_g2.plotly_chart(fig_line, use_container_width=True)

    # ==================================================
    # KAYIT EKLE / AKTAR
    # ==================================================

    elif secim == "📂 Kayıt Ekle / Aktar":
        st.header("📂 Kayıt Ekle / Excel Aktar")

        if yetki != "Yönetici":
            st.warning("Bu alana sadece yöneticiler erişebilir.")
        else:
            t1, t2 = st.tabs(["✍️ Manuel Ekle", "📂 Excel Aktar"])

            with t1:
                with st.form("manuel_form"):
                    s = st.text_input("Sicil")
                    a = st.text_input("Ad Soyad")
                    tel = st.text_input("Telefon")
                    u = st.text_area("Ürünler")
                    adet = st.number_input("Adet", min_value=1, value=1)

                    kaydet = st.form_submit_button("Kaydet")

                    if kaydet:
                        if not s or not a or not u:
                            st.error("Sicil, Ad Soyad ve Ürünler alanları boş bırakılamaz.")
                        else:
                            c.execute("""
                                INSERT INTO siparisler
                                (sicil_no, uye_adi, telefon_no, urunler, adet, durum, tarih, silindi)
                                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                            """, (
                                s,
                                a,
                                tel,
                                u,
                                adet,
                                DURUMLAR[0],
                                bugun()
                            ))
                            conn.commit()
                            log_ekle(mevcut_user, f"Manuel kayıt eklendi: {s} - {a}")
                            st.success("Kayıt eklendi.")
                            st.rerun()

            with t2:
                st.write("### Excel Aktar")

                st.caption("Beklenen kolonlar: sicil_no, uye_adi, telefon_no, urunler")

                up = st.file_uploader("Dosya Seç", type=["xlsx"])

                if up:
                    df_up = pd.read_excel(up, dtype=str)
                    st.write("Ön izleme")
                    st.dataframe(df_up.head(20), use_container_width=True)

                    gerekli_kolonlar = ["sicil_no", "uye_adi", "telefon_no", "urunler"]
                    eksik_kolonlar = [k for k in gerekli_kolonlar if k not in df_up.columns]

                    if eksik_kolonlar:
                        st.error(f"Eksik kolonlar: {', '.join(eksik_kolonlar)}")
                    else:
                        bos_sicil = df_up["sicil_no"].isna().sum()
                        bos_ad = df_up["uye_adi"].isna().sum()
                        bos_urun = df_up["urunler"].isna().sum()

                        st.info(
                            f"Dosyada {len(df_up)} satır var. "
                            f"Boş sicil: {bos_sicil}, boş ad: {bos_ad}, boş ürün: {bos_urun}"
                        )

                        if st.button("Excel'den Aktar"):
                            aktarim_id = datetime.now().strftime("AKT-%Y%m%d-%H%M%S")

                            eklenen = 0
                            atlanan = 0

                            for _, r in df_up.iterrows():
                                sicil = str(r.get("sicil_no", "")).strip()
                                ad = str(r.get("uye_adi", "")).strip()
                                tel = str(r.get("telefon_no", "")).strip()
                                urun = str(r.get("urunler", "")).strip()

                                if sicil == "" or ad == "" or urun == "":
                                    atlanan += 1
                                    continue

                                # Basit mükerrer kontrol
                                c.execute("""
                                    SELECT COUNT(*) 
                                    FROM siparisler
                                    WHERE silindi = 0 
                                    AND sicil_no = ?
                                    AND urunler = ?
                                    AND durum != 'Teslim edildi'
                                """, (sicil, urun))

                                var_mi = c.fetchone()[0]

                                if var_mi > 0:
                                    atlanan += 1
                                    continue

                                c.execute("""
                                    INSERT INTO siparisler
                                    (sicil_no, uye_adi, telefon_no, urunler, adet, durum, tarih, aktarim_id, silindi)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                                """, (
                                    sicil,
                                    ad,
                                    tel,
                                    urun,
                                    1,
                                    DURUMLAR[0],
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
                                f"Aktarım tamamlandı. Aktarım ID: {aktarim_id}. "
                                f"Eklenen: {eklenen}, Atlanan: {atlanan}"
                            )

                            st.rerun()

    # ==================================================
    # YÖNETİM
    # ==================================================

    elif secim == "🗑️ Yönetim":
        st.header("🗑️ Kayıt Yönetimi")

        if yetki != "Yönetici":
            st.warning("Bu alana erişim yetkiniz yok.")
        else:
            t1, t2, t3, t4 = st.tabs([
                "Tekil Sil",
                "Filtreli Toplu Sil",
                "Aktarım ID ile Sil",
                "Arşivlenenler"
            ])

            # ------------------------------------------
            # TEKİL SİL
            # ------------------------------------------

            with t1:
                st.subheader("Tekil Kayıt Sil")

                df_one = pd.read_sql_query("""
                    SELECT id, sicil_no, uye_adi, urunler, durum, tarih, aktarim_id
                    FROM siparisler
                    WHERE silindi = 0
                    ORDER BY id DESC
                """, conn)

                if df_one.empty:
                    st.info("Silinecek aktif kayıt yok.")
                else:
                    arama = st.text_input("İsim, sicil veya ID ile ara")

                    if arama:
                        df_one = df_one[
                            df_one["uye_adi"].str.contains(arama, case=False, na=False) |
                            df_one["sicil_no"].str.contains(arama, case=False, na=False) |
                            df_one["id"].astype(str).str.contains(arama, na=False)
                        ]

                    st.dataframe(df_one.head(100), use_container_width=True)

                    secilen_id = st.number_input("Silinecek ID", min_value=1, step=1)

                    col1, col2 = st.columns(2)

                    if col1.button("Seçili ID'yi Arşivle / Sil"):
                        kaydi_arsivle(secilen_id, mevcut_user)
                        st.success(f"ID {secilen_id} arşivlendi.")
                        st.rerun()

                    if col2.button("Seçili ID'yi Kalıcı Sil"):
                        kaydi_kalici_sil(secilen_id, mevcut_user)
                        st.warning(f"ID {secilen_id} kalıcı olarak silindi.")
                        st.rerun()

            # ------------------------------------------
            # FİLTRELİ TOPLU SİL
            # ------------------------------------------

            with t2:
                st.subheader("Filtreli Toplu Sil")

                durum_filtre = st.selectbox("Duruma göre filtrele", ["Tümü"] + DURUMLAR)
                tarih_filtre = st.text_input("Tarihe göre filtrele", value=bugun())

                query = """
                    SELECT id, sicil_no, uye_adi, urunler, durum, tarih, aktarim_id
                    FROM siparisler
                    WHERE silindi = 0
                """
                params = []

                if durum_filtre != "Tümü":
                    query += " AND durum = ?"
                    params.append(durum_filtre)

                if tarih_filtre:
                    query += " AND tarih = ?"
                    params.append(tarih_filtre)

                df_bulk = pd.read_sql_query(query + " ORDER BY id DESC", conn, params=params)

                st.write(f"Filtreye uyan kayıt sayısı: **{len(df_bulk)}**")
                st.dataframe(df_bulk.head(200), use_container_width=True)

                onay = st.checkbox("Bu filtreye uyan kayıtları silmek istediğimi onaylıyorum.")

                col1, col2 = st.columns(2)

                if col1.button("Filtrelenenleri Arşivle / Sil"):
                    if onay and len(df_bulk) > 0:
                        ids = df_bulk["id"].tolist()

                        for sid in ids:
                            c.execute("""
                                UPDATE siparisler
                                SET silindi = 1, silinme_tarihi = ?
                                WHERE id = ?
                            """, (simdi(), sid))

                        conn.commit()
                        log_ekle(mevcut_user, f"{len(ids)} kayıt filtreli olarak arşivlendi/silindi.")
                        st.success(f"{len(ids)} kayıt arşivlendi.")
                        st.rerun()
                    else:
                        st.error("Silme işlemi için onay kutusunu işaretlemelisin.")

                if col2.button("Filtrelenenleri Kalıcı Sil"):
                    if onay and len(df_bulk) > 0:
                        ids = df_bulk["id"].tolist()

                        for sid in ids:
                            c.execute("DELETE FROM siparisler WHERE id = ?", (sid,))

                        conn.commit()
                        log_ekle(mevcut_user, f"{len(ids)} kayıt filtreli olarak kalıcı silindi.")
                        st.warning(f"{len(ids)} kayıt kalıcı olarak silindi.")
                        st.rerun()
                    else:
                        st.error("Kalıcı silme için onay kutusunu işaretlemelisin.")

            # ------------------------------------------
            # AKTARIM ID İLE SİL
            # ------------------------------------------

            with t3:
                st.subheader("Aktarım ID ile Toplu Sil")

                df_akt = pd.read_sql_query("""
                    SELECT 
                        aktarim_id,
                        COUNT(*) AS kayit_sayisi,
                        MIN(tarih) AS ilk_tarih,
                        MAX(tarih) AS son_tarih
                    FROM siparisler
                    WHERE silindi = 0
                    AND aktarim_id IS NOT NULL
                    GROUP BY aktarim_id
                    ORDER BY aktarim_id DESC
                """, conn)

                if df_akt.empty:
                    st.info("Aktarım ID bulunan aktif kayıt yok.")
                else:
                    st.dataframe(df_akt, use_container_width=True)

                    secilen_akt = st.selectbox(
                        "Silinecek Aktarım ID",
                        df_akt["aktarim_id"].tolist()
                    )

                    adet = int(df_akt[df_akt["aktarim_id"] == secilen_akt]["kayit_sayisi"].iloc[0])

                    st.warning(f"Bu işlem {adet} kaydı etkileyecek.")

                    onay_akt = st.checkbox("Bu aktarımı silmek istediğimi onaylıyorum.")

                    col1, col2 = st.columns(2)

                    if col1.button("Bu Aktarımı Arşivle / Sil"):
                        if onay_akt:
                            c.execute("""
                                UPDATE siparisler
                                SET silindi = 1, silinme_tarihi = ?
                                WHERE aktarim_id = ?
                            """, (simdi(), secilen_akt))
                            conn.commit()

                            log_ekle(mevcut_user, f"Aktarım ID {secilen_akt} arşivlendi/silindi. Kayıt: {adet}")
                            st.success(f"{adet} kayıt arşivlendi.")
                            st.rerun()
                        else:
                            st.error("Onay kutusunu işaretlemelisin.")

                    if col2.button("Bu Aktarımı Kalıcı Sil"):
                        if onay_akt:
                            c.execute("DELETE FROM siparisler WHERE aktarim_id = ?", (secilen_akt,))
                            conn.commit()

                            log_ekle(mevcut_user, f"Aktarım ID {secilen_akt} kalıcı silindi. Kayıt: {adet}")
                            st.warning(f"{adet} kayıt kalıcı olarak silindi.")
                            st.rerun()
                        else:
                            st.error("Onay kutusunu işaretlemelisin.")

            # ------------------------------------------
            # ARŞİVLENENLER
            # ------------------------------------------

            with t4:
                st.subheader("Arşivlenen / Silinen Kayıtlar")

                df_arc = pd.read_sql_query("""
                    SELECT id, sicil_no, uye_adi, urunler, durum, tarih, aktarim_id, silinme_tarihi
                    FROM siparisler
                    WHERE silindi = 1
                    ORDER BY id DESC
                """, conn)

                st.dataframe(df_arc.head(500), use_container_width=True)

                geri_id = st.number_input("Geri alınacak ID", min_value=1, step=1)

                if st.button("Bu Kaydı Geri Al"):
                    c.execute("""
                        UPDATE siparisler
                        SET silindi = 0, silinme_tarihi = NULL
                        WHERE id = ?
                    """, (geri_id,))
                    conn.commit()

                    log_ekle(mevcut_user, f"ID {geri_id} arşivden geri alındı.")
                    st.success(f"ID {geri_id} geri alındı.")
                    st.rerun()

    # ==================================================
    # LOG
    # ==================================================

    elif secim == "🕒 Log":
        st.header("🕒 İşlem Logları")

        t1, t2 = st.tabs(["Genel Log", "Durum Geçmişi"])

        with t1:
            df_log = pd.read_sql_query("""
                SELECT * FROM islem_gecmisi
                ORDER BY id DESC
            """, conn)

            st.dataframe(df_log, use_container_width=True)

        with t2:
            df_durum_log = pd.read_sql_query("""
                SELECT * FROM durum_gecmisi
                ORDER BY id DESC
            """, conn)

            st.dataframe(df_durum_log, use_container_width=True)

    # --------------------------------------------------
    # ÇIKIŞ
    # --------------------------------------------------

    if st.sidebar.button("🚪 Çıkış"):
        del st.session_state["kullanici"]
        del st.session_state["yetki"]
        st.rerun()
