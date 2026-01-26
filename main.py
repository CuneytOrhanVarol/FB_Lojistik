# --- 1. SİPARİŞ TAKİP VE DETAYLI ARAMA ---
    if secim == "Sipariş Takip / Operasyon":
        st.header("🔎 Detaylı ve Toplu Arama Paneli")
        
        with st.expander("🔍 Gelişmiş Filtreleme (Tekli veya Toplu)", expanded=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                search_id = st.text_input("ID'ye göre ara")
                search_name = st.text_input("İsim Soyad'a göre ara")
                search_status = st.selectbox("Durum Filtrele", ["Tümü"] + DURUMLAR)
            
            with c2:
                # ALT ALTA VEYA VİRGÜLLÜ SİCİL YAPISTIRMA ALANI
                search_sicil_bulk = st.text_area("Toplu Sicil No Sorgulama (Sicilleri alt alta veya virgülle ayırarak yapıştırın)")
            
            search_btn = st.button("Kayıtları Filtrele / Getir")

        # Sorgu Oluşturma
        query = """SELECT id as 'ID', sicil_no as 'Sicil No', uye_adi as 'Ad Soyad', 
                   urunler as 'Ürünler', adet as 'Adet', durum as 'Durum', 
                   kargo_no as 'Kargo No', kargo_tarihi as 'Kargo Tarihi', tarih as 'Kayıt Tarihi' 
                   FROM siparisler WHERE 1=1"""
        params = []
        
        if search_id:
            query += " AND id = ?"
            params.append(search_id)
        
        # TOPLU SİCİL NO İŞLEME MANTIĞI
        if search_sicil_bulk:
            # Satırlara veya virgüllere göre parçala, boşlukları temizle
            siciller = [s.strip() for s in search_sicil_bulk.replace('\n', ',').split(',') if s.strip()]
            if siciller:
                placeholders = ','.join(['?'] * len(siciller))
                query += f" AND sicil_no IN ({placeholders})"
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
            
            # --- GÜNCELLEME FORMU ---
            st.subheader("🛠️ Toplu veya Tekil Güncelleme")
            df['secim_etiketi'] = df['Sicil No'].astype(str) + " - " + df['Ad Soyad'] + " (ID: " + df['ID'].astype(str) + ")"
            etiket_to_id = dict(zip(df['secim_etiketi'], df['ID']))
            
            with st.form("güncelleme_formu"):
                col1, col2 = st.columns(2)
                # Filtreleme yapıldıysa sonuçları seçmek çok kolaylaşır
                secilen_etiketler = col1.multiselect("Güncellenecek Kayıtları Seçin", df['secim_etiketi'].tolist())
                yeni_statü = col2.selectbox("Yeni Durum Seçin", DURUMLAR)
                col3, col4 = st.columns(2)
                yeni_kargo_no = col3.text_input("Kargo No")
                yeni_kargo_tarih = col4.text_input("Kargo Tarihi")
                
                if st.form_submit_button("Seçili Kayıtları Güncelle"):
                    if secilen_etiketler:
                        ids = [etiket_to_id[e] for e in secilen_etiketler]
                        for s_id in ids:
                            c.execute("UPDATE siparisler SET durum = ?, kargo_no = ?, kargo_tarihi = ? WHERE id = ?", (yeni_statü, yeni_kargo_no, yeni_kargo_tarih, s_id))
                        conn.commit()
                        log_ekle(mevcut_user, f"{len(ids)} kaydı '{yeni_statü}' olarak güncelledi.")
                        st.success("Başarıyla güncellendi!")
                        st.rerun()
        else:
            st.warning("Aranan kriterlerde kayıt bulunamadı.")
