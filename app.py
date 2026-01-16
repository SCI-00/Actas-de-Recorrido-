import streamlit as st
import pandas as pd
from datetime import date
import database
import visualizations
import file_parser
import io
import os

# --- INIT ---
st.set_page_config(page_title="NOM-019 Dashboard", page_icon="🛡️", layout="wide")
database.init_db()

# --- CONSTANTS ---
LISTA_CEDIS = [
    "Acayucan", "Ciudad Neza", "Coatzacoalcos", "Colonia Roma", "Cordoba", "Cuautitlan", 
    "Ecatepec", "Izucar de Matamoros", "Martinez de la Torre", "Poza Rica Veracruz", 
    "Puebla Norte", "Puebla Sur", "San Andres Tuxtla", "Satelite", "Tehuacan", "Texcoco", 
    "Tlalnepantla", "Tlalpan (Acoxpa)", "Toluca", "Veracruz", "Xalapa", "Ensenada", 
    "Mexicali", "Tijuana", "La Paz", "Chihuahua OMNILIFE ft SEYTÚ", "Ciudad Juárez", 
    "Saltillo", "Torreon", "Durango", "Guadalupe", "Monterrey", "Culiacan", "Los Mochis", 
    "Mazatlan", "Hermosillo", "San Luis Rio Colorado", "Ciudad Victoria", "Matamoros", 
    "Nuevo Laredo", "Reynosa", "Tampico", "Aguascalientes", "Colima", "Irapuato", "León", 
    "Acapulco", "Pachuca", "Ecocentro", "Patria (Amistad)", "Prisciliano", "Puerto Vallarta", 
    "Tlaquepaque", "La Piedad", "Lazaro Cardenas", "Morelia", "Uruapan", "Cuernavaca", 
    "Tepic", "Queretaro", "San Luis Potosi", "Zacatecas", "Campeche", "Cancún", "Chetumal", 
    "Ciudad del Carmen", "Comalcalco", "Comitan", "Huajuapan de Leon", "Merida", 
    "Merida Norte", "Merida Hub", "Oaxaca", "Playa del Carmen", "Puerto Escondido", 
    "Salina Cruz", "San Cristobal", "Tapachula", "Tenosique", "Tuxtepec", 
    "Tuxtla Gutierrez", "Villahermosa"
]
LISTA_CEDIS.sort()

ESTADOS_MX = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas", "Chihuahua",
    "Ciudad de México", "Coahuila", "Colima", "Durango", "Guanajuato", "Guerrero", "Hidalgo",
    "Jalisco", "México", "Michoacán", "Morelos", "Nayarit", "Nuevo León", "Oaxaca", "Puebla",
    "Querétaro", "Quintana Roo", "San Luis Potosí", "Sinaloa", "Sonora", "Tabasco", "Tamaulipas",
    "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas"
]

def save_uploaded_file(uploadedfile):
    if uploadedfile is None: return None
    if not os.path.exists("evidencias"): os.makedirs("evidencias")
    file_path = os.path.join("evidencias", uploadedfile.name)
    with open(file_path, "wb") as f:
        f.write(uploadedfile.getbuffer())
    return file_path

def main():
    st.sidebar.title("🛡️ NOM-019")
    menu = st.sidebar.radio("Navegación", 
        ["📊 Dashboard", "📝 Nuevo Hallazgo", "📥 Carga Masiva", "🛠️ Gestión de Registros"]
    )
    
    if menu == "📊 Dashboard":
        show_dashboard()
    elif menu == "📝 Nuevo Hallazgo":
        show_form()
    elif menu == "📥 Carga Masiva":
        show_import()
    elif menu == "🛠️ Gestión de Registros":
        show_management()

def show_dashboard():
    st.title("📊 Tablero de Cumplimiento")
    df = database.get_findings()
    
    if df.empty:
        st.info("No hay datos para mostrar.")
        return

    # Filters
    st.sidebar.markdown("### Filtros")
    f_cedis = st.sidebar.multiselect("CEDIS", df['cedis'].unique())
    f_riesgo = st.sidebar.multiselect("Riesgo", ["Alto", "Medio", "Bajo"])
    
    if f_cedis: df = df[df['cedis'].isin(f_cedis)]
    if f_riesgo: df = df[df['riesgo'].isin(f_riesgo)]
    
    # KPIs
    st.markdown("### Resumen Ejecutivo")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total", len(df))
    k2.metric("Abiertos", len(df[df['estatus']=="Abierto"]), delta_color="inverse")
    k3.metric("Cerrados", len(df[df['estatus']=="Cerrado"]), delta_color="normal")
    k4.metric("Alto Riesgo", len(df[df['riesgo']=="Alto"]), delta_color="inverse")
    
    st.divider()
    
    # Charts
    c1, c2 = st.columns([1, 1])
    fig_risk, fig_status, fig_map = visualizations.plot_kpis_risk(df)
    
    with c1:
        if fig_risk: st.plotly_chart(fig_risk, use_container_width=True)
    with c2:
        if fig_status: st.plotly_chart(fig_status, use_container_width=True)
        
    st.subheader("Mapa de Calor (Por Estado)")
    if fig_map: st.plotly_chart(fig_map, use_container_width=True)
    
    st.subheader("Cronograma de Actividades")
    fig_g = visualizations.plot_gantt(df)
    if fig_g: st.plotly_chart(fig_g, use_container_width=True)
    
    if st.button("📥 Descargar Reporte Ejecutivo (Excel)"):
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            # 1. Hoja de Datos
            df.to_excel(writer, index=False, sheet_name='Hallazgos')
            
            # 2. Hoja de Gráficas
            workbook = writer.book
            worksheet = workbook.add_worksheet('Gráficas Ejecutivas')
            
            # --- PREPARAR DATOS (Tablas dinámicas ocultas) ---
            # Riesgos
            riesgos = df['riesgo'].value_counts()
            worksheet.write(0, 0, "Riesgo")
            worksheet.write(0, 1, "Total")
            for i, (k, v) in enumerate(riesgos.items()):
                worksheet.write(i+1, 0, k)
                worksheet.write(i+1, 1, v)
                
            # Estatus
            estatus = df['estatus'].value_counts()
            worksheet.write(0, 3, "Estatus")
            worksheet.write(0, 4, "Total")
            for i, (k, v) in enumerate(estatus.items()):
                worksheet.write(i+1, 3, k)
                worksheet.write(i+1, 4, v)

            # Top CEDIS (Solo Top 5)
            cedis = df['cedis'].value_counts().head(5)
            worksheet.write(0, 6, "Top CEDIS")
            worksheet.write(0, 7, "Total")
            for i, (k, v) in enumerate(cedis.items()):
                worksheet.write(i+1, 6, k)
                worksheet.write(i+1, 7, v)
            
            # Estados
            estados = df['estado_geo'].value_counts().head(10) if 'estado_geo' in df.columns else pd.Series()
            worksheet.write(0, 9, "Estado")
            worksheet.write(0, 10, "Total")
            for i, (k, v) in enumerate(estados.items()):
                worksheet.write(i+1, 9, k)
                worksheet.write(i+1, 10, v)

            # --- INSERTAR GRÁFICAS ---
            
            # 1. Riesgos (Pastel)
            chart_pie = workbook.add_chart({'type': 'pie'})
            chart_pie.add_series({
                'name': 'Riesgos',
                'categories': ['Gráficas Ejecutivas', 1, 0, len(riesgos), 0],
                'values':     ['Gráficas Ejecutivas', 1, 1, len(riesgos), 1],
                'data_labels': {'percentage': True}
            })
            chart_pie.set_title({'name': 'Nivel de Riesgo'})
            chart_pie.set_style(10)
            worksheet.insert_chart('A10', chart_pie)

            # 2. Estatus (Columnas)
            chart_col = workbook.add_chart({'type': 'column'})
            chart_col.add_series({
                'name': 'Estatus',
                'categories': ['Gráficas Ejecutivas', 1, 3, len(estatus), 3],
                'values':     ['Gráficas Ejecutivas', 1, 4, len(estatus), 4],
                'data_labels': {'value': True}
            })
            chart_col.set_title({'name': 'Estatus General'})
            chart_col.set_style(11)
            worksheet.insert_chart('E10', chart_col)
            
            # 3. Top CEDIS (Barras)
            chart_bar = workbook.add_chart({'type': 'bar'})
            chart_bar.add_series({
                'name': 'CEDIS',
                'categories': ['Gráficas Ejecutivas', 1, 6, len(cedis), 6],
                'values':     ['Gráficas Ejecutivas', 1, 7, len(cedis), 7],
                'data_labels': {'value': True},
                'fill': {'color': '#1E3A8A'}
            })
            chart_bar.set_title({'name': 'Top 5 CEDIS'})
            chart_bar.set_style(12)
            worksheet.insert_chart('A26', chart_bar)
            
            # 4. Estados (Columnas) - Si hay datos
            if not estados.empty:
                chart_state = workbook.add_chart({'type': 'column'})
                chart_state.add_series({
                    'name': 'Estados',
                    'categories': ['Gráficas Ejecutivas', 1, 9, len(estados), 9],
                    'values':     ['Gráficas Ejecutivas', 1, 10, len(estados), 10],
                })
                chart_state.set_title({'name': 'Hallazgos por Estado (Top 10)'})
                worksheet.insert_chart('E26', chart_state)

        st.download_button("📥 Descargar Reporte Ejecutivo", buffer, "Reporte_NOM019_Ejecutivo.xlsx")

def show_form():
    st.header("📝 Registro Manual Detallado")
    with st.form("entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        sesion = c1.text_input("No. Sesión")
        cedis = c2.selectbox("CEDIS", LISTA_CEDIS)
        estado = c3.selectbox("Estado (Geo)", ESTADOS_MX)
        
        desc = st.text_area("Descripción del Hallazgo")
        
        c4, c5 = st.columns(2)
        riesgo = c4.selectbox("Nivel de Riesgo", ["Bajo", "Medio", "Alto"])
        tipo = c5.selectbox("Tipo", ["Documental", "Inversión", "Proceso"])
        
        c6, c7 = st.columns(2)
        resp = c6.text_input("Responsable")
        acciones = c7.text_area("Acciones Inmediatas")
        
        c8, c9 = st.columns(2)
        f_det = c8.date_input("Fecha Detección", value=date.today())
        f_com = c9.date_input("Fecha Compromiso")
        
        # Evidence
        evidencia = st.file_uploader("Evidencia Fotográfica", type=["png", "jpg", "jpeg"])
        
        if st.form_submit_button("Guardar Registro"):
            path = save_uploaded_file(evidencia)
            success = database.add_finding({
                "numero_sesion": sesion,
                "cedis": cedis,
                "estado_geo": estado,
                "hallazgo": desc,
                "riesgo": riesgo,
                "tipo_hallazgo": tipo,
                "responsable": resp,
                "acciones_inmediatas": acciones,
                "fecha_hallazgo": f_det,
                "fecha_compromiso": f_com,
                "evidencia_path": path
            })
            if success: st.success("Guardado exitosamente.")
            else: st.error("Error al guardar.")

def show_import():
    st.header("📥 Carga Masiva Inteligente")
    st.info("Soporta: Excel (Matriz General) y PDF (Actas de Recorrido)")
    
    uploaded = st.file_uploader("Arrastra tu archivo aquí", type=["xlsx", "pdf", "docx"])
    
    if uploaded:
        ext = uploaded.name.split('.')[-1].lower()
        
        if ext == "xlsx":
            df = file_parser.parse_excel_matrix(uploaded)
            if isinstance(df, pd.DataFrame):
                st.write(f"Vista previa ({len(df)} registros):")
                st.dataframe(df.head())
                if st.button("Importar Excel"):
                    count = 0 
                    for _, row in df.iterrows():
                        if database.add_finding(row.to_dict()): count += 1
                    st.success(f"Importados {count} registros.")
        
        elif ext == "pdf":
            st.warning("⏳ Analizando PDF... (Esto puede tardar unos segundos)")
            try:
                findings = file_parser.parse_pdf_acta(uploaded)
                if findings:
                    st.success(f"✅ Se encontraron {len(findings)} hallazgos en el PDF.")
                    df_pdf = pd.DataFrame(findings)
                    edited = st.data_editor(df_pdf)
                    if st.button("Guardar Hallazgos del PDF"):
                        for _, row in edited.iterrows():
                            database.add_finding(row.to_dict())
                        st.success("Guardados.")
                else:
                    st.error("❌ No se pudieron extraer datos.")
                    st.markdown("""
                    **Posibles causas:**
                    1. El PDF es una imagen escaneada (no tiene texto seleccionable).
                    2. Los encabezados de la tabla no coinciden (Buscamos: 'Hallazgo', 'Acciones', 'Responsable').
                    """)
            except Exception as e:
                st.error(f"Error técnico leyendo PDF: {e}")

def show_management():
    st.header("🛠️ Gestión de Registros")
    
    tab_edit, tab_del, tab_ver = st.tabs(["✏️ Editar Datos", "🗑️ Eliminar Registros", "📷 Ver Evidencia"])
    
    df = database.get_findings()
    
    with tab_edit:
        st.info("Edita datos incorrectos directamente en la tabla.")
        edited_df = st.data_editor(df, num_rows="dynamic", key="data_editor")
        
        if st.button("Guardar Cambios (Edición)"):
            count = 0
            for _, row in edited_df.iterrows():
                if "id" in row and pd.notna(row["id"]):
                    database.update_finding(row["id"], row.to_dict())
                    count += 1
            st.success(f"Actualizados {count} registros.")
            st.rerun()

    with tab_del:
        if df.empty:
            st.write("No hay registros para borrar.")
        else:
            st.warning("⚠️ Precaución: Esta acción es irreversible.")
            
            # Create a display label for the multiselect
            df['label'] = df.apply(lambda x: f"ID {x['id']}: {x['cedis']} - {str(x['hallazgo'])[:30]}...", axis=1)
            
            ids_to_delete = st.multiselect(
                "Selecciona los registros a eliminar:",
                options=df['id'].tolist(),
                format_func=lambda i: df[df['id'] == i]['label'].values[0]
            )
            
            if st.button("🗑️ Eliminar Seleccionados Definitivamente", type="primary"):
                if ids_to_delete:
                    for i in ids_to_delete:
                        database.delete_finding(i)
                    st.success(f"Eliminados {len(ids_to_delete)} registros.")
                    st.rerun()
                else:
                    st.info("Selecciona algo primero.")

    with tab_ver:
        st.markdown("### 🖼️ Visor de Evidencias")
        # Filtrar solo los que tienen path
        if 'evidencia_path' in df.columns:
            df_imgs = df[df['evidencia_path'].notna() & (df['evidencia_path'] != "")]
            df_imgs = df_imgs[df_imgs['evidencia_path'] != "None"] # string cleanup
            
            if df_imgs.empty:
                st.info("No hay registros que tengan evidencia fotográfica adjunta.")
            else:
                # Selectbox para elegir
                df_imgs['vis_label'] = df_imgs.apply(
                    lambda x: f"ID {x['id']} | {x['cedis']} | {str(x['hallazgo'])[:40]}...", axis=1
                )
                
                sel_id = st.selectbox(
                    "Selecciona el hallazgo para ver su foto:",
                    df_imgs['id'].tolist(),
                    format_func=lambda i: df_imgs[df_imgs['id'] == i]['vis_label'].values[0]
                )
                
                # Mostrar imagen
                if sel_id:
                    row = df_imgs[df_imgs['id'] == sel_id].iloc[0]
                    path = row['evidencia_path']
                    
                    st.write(f"**Archivo:** `{path}`")
                    
                    if os.path.exists(path):
                        st.image(path, caption=f"Evidencia del ID {sel_id}", use_container_width=True)
                    else:
                        st.error("⚠️ El archivo de imagen consta en base de datos pero no se encuentra en la carpeta 'evidencias'.")
        else:
            st.warning("La columna 'evidencia_path' no existe en la base de datos.")

if __name__ == "__main__":
    main()
