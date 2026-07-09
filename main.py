import streamlit as st

from database import veritabani_hazirla
from login import giris_ekrani
from operasyon import operasyon_paneli
from aktarim import kayit_ekle_aktar
from temizlik import hatali_kayit_temizligi, log_ekrani


st.set_page_config(
    page_title="FB Operasyon Merkezi",
    layout="wide"
)

veritabani_hazirla()


if "kullanici" not in st.session_state:
    giris_ekrani()
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


if secim == "📦 Operasyon Paneli":
    operasyon_paneli(mevcut_user, yetki)

elif secim == "📂 Kayıt Ekle / Aktar":
    kayit_ekle_aktar(mevcut_user)

elif secim == "🧹 Hatalı Kayıt Temizliği":
    hatali_kayit_temizligi(mevcut_user)

elif secim == "🕒 Log":
    log_ekrani()


if st.sidebar.button("🚪 Çıkış"):
    st.session_state.clear()
    st.rerun()
