# --- 1. SİPARİŞ TAKİP VE DETAYLI (TOPLU) ARAMA ---
    if secim == "Sipariş Takip / Operasyon":
        st.header("🔎 Detaylı ve Toplu Arama")
        
        with st.expander("🔍 Gelişmiş Filtreleme (Çoklu arama için aralara virgül koyun)", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            search_id = c1.text_input("ID(ler) (Örn: 1, 5, 10)")
            search_sicil = c2.text_input("Sicil No(lar) (Örn: 1001, 1005)")
            search_name = c3.text_input("İsim Soyad")
            search_status = c4.selectbox("Durum Filtrele", ["Tümü"] + DURUMLAR)
            search_btn = st.button("Filtrele")

        # Sorgu Oluşturma
        query = """SELECT id as 'ID', sicil_no as 'Sicil No', uye_adi as 'Ad Soyad', 
                   urunler as 'Ürünler', adet as 'Adet', durum as 'Durum', 
                   kargo_no as 'Kargo No', kargo_tarihi as 'Kargo Tarihi', tarih as 'Kayıt Tarihi' 
                   FROM siparisler WHERE 1=1"""
        params = []
        
        # TOPLU ID ARAMA
        if search_id:
            ids = [i.strip() for i in search_id.split(",") if i.strip().isdigit()]
            if ids:
                query += f" AND id IN ({','.join(['?']*len(ids))})"
                params.extend(ids)
        
        # TOPLU SİCİL NO ARAMA
        if search_sicil:
            siciller = [s.strip() for s in search_sicil.split(",") if s.strip()]
            if siciller:
                query += f" AND sicil_no IN ({','.join(['?']*len(siciller))})"
                params.extend(siciller)

        if search_name:
            query += " AND uye_adi LIKE ?"
            params.append(f"%{search_name}%")
            
        if search_status != "Tümü":
            query += " AND durum = ?"
            params.append(search_status)
            
        query += " ORDER BY id DESC"
        df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            st.subheader(f"📋 Listelenen Siparişler ({len(df)} Kayıt)")
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.divider()
            
            # --- GÜNCELLEME BÖLÜMÜ ---
            st.subheader("🛠️ Seçili Kayıtları Güncelle")
            df['secim_etiketi'] = df['Sicil No'].astype(str) + " - " + df['Ad Soyad'] + " (ID: " + df['ID'].astype(str) + ")"
            etiket_to_id = dict(zip(df['secim_etiketi'], df['ID']))
            
            with st.form("güncelleme_formu"):
                col1, col2 = st.columns(2)
                # Filtrelenen sonuçları multiselect'e varsayılan olarak eklemiyoruz ama listeden seçimi kolaylaştırıyoruz
                secilen_etiketler = col1.multiselect("Güncellenecek Kayıtları Seçin", df['secim_etiketi'].tolist())
                yeni_statü = col2.selectbox("Yeni Durum Seçin", DURUMLAR)
                col3, col4 = st.columns(2)
                yeni_kargo_no = col3.text_input("Kargo No")
                yeni_kargo_tarih = col4.text_input("Kargo Tarihi")
                
                if st.form_submit_button("Seçili Kayıtları Güncelle"):
                    if secilen_etiketler:
                        ids_to_update = [etiket_to_id[e] for e in secilen_etiketler]
                        for s_id in ids_to_update:
                            c.execute("UPDATE siparisler SET durum = ?, kargo_no = ?, kargo_tarihi = ? WHERE id = ?", (yeni_statü, yeni_kargo_no, yeni_kargo_tarih, s_id))
                        conn.commit()
                        log_ekle(mevcut_user, f"{len(ids_to_update)} kaydı toplu olarak '{yeni_statü}' yaptı.")
                        st.success(f"{len(ids_to_update)} kayıt başarıyla güncellendi!")
                        st.rerun()
        else:
            st.warning("Aranan kriterlerde kayıt bulunamadı.")
