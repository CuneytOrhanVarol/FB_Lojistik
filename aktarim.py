import streamlit as st
import pandas as pd
from database import baglan, bugun, log_ekle
from login import DURUMLAR, TEDARIKCI_DURUMLARI


def operasyon_paneli(mevcut_user, yetki):
    st.header("📦 Operasyon Paneli")
    st.info("Sayfalı listeleme aktif. Büyük veri çökme riskini azaltır.")

    col1, col2, col3 = st.columns([2, 1, 1])

    arama = col1.text_input("İsim / sicil / telefon ara")
    durum_filtre = col2.selectbox("Durum", ["Tümü"] + DURUMLAR)
    limit = col3.selectbox("Sayfa başı kayıt", [100, 300, 500, 1000, 5000], index=1)

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

    if "liste_df" not in st.session_state:
        return

    df = st.session_state["liste_df"].copy()

    st.write(f"Listelenen kayıt sayısı: **{len(df)}**")

    if df.empty:
        st.warning("Kayıt bulunamadı.")
        return

    if "Seç" not in df.columns:
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

    if secilenler.empty:
        return

    st.subheader(f"Seçilen kayıt sayısı: {len(secilenler)}")

    yeni_durum = st.selectbox("Yeni durum", DURUMLAR)

    if st.button("Seçilenlerin Durumunu Güncelle"):
        conn = baglan()
        c = conn.cursor()

        for _, row in secilenler.iterrows():
            sid = int(row["id"])
            kargo_no = row.get("kargo_no", "")

            if yeni_durum == "Kargoya verildi":
                c.execute("""
                    UPDATE siparisler
                    SET durum = ?,
                        kargo_tarihi = ?,
                        kargo_no = ?
                    WHERE id = ?
                """, (yeni_durum, bugun(), kargo_no, sid))
            else:
                c.execute("""
                    UPDATE siparisler
                    SET durum = ?,
                        kargo_no = ?
                    WHERE id = ?
                """, (yeni_durum, kargo_no, sid))

        conn.commit()
        conn.close()

        log_ekle(mevcut_user, f"{len(secilenler)} kayıt '{yeni_durum}' yapıldı.")

        del st.session_state["liste_df"]
        st.success("Durum güncellendi.")
        st.rerun()
