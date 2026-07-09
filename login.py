
import streamlit as st

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


def yetki_bul(kullanici):
    if kullanici in YONETICILER:
        return "Yönetici"
    return "Tedarikçi"


def giris_ekrani():
    st.title("🛡️ FB Operasyon Merkezi")

    kullanici_sec = st.selectbox("Kullanıcı", list(KULLANICILAR.keys()))
    sifre = st.text_input("Şifre", type="password")

    if st.button("Giriş Yap"):
        if KULLANICILAR.get(kullanici_sec) == sifre:
            st.session_state["kullanici"] = kullanici_sec
            st.session_state["yetki"] = yetki_bul(kullanici_sec)
            st.rerun()
        else:
            st.error("Hatalı şifre")
