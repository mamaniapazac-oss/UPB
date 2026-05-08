import streamlit as st
import random
import datetime
import database_manager
import grafo_espacial

# Configuración inicial
st.set_page_config(layout="wide", page_title="Sistema UPI", page_icon="🏢")

# ==========================================
# LÓGICA DE TIEMPO REAL AUTOMATIZADA
# ==========================================
def obtener_contexto_actual():
    ahora = datetime.datetime.now()
    dias_espanol = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_actual = dias_espanol[ahora.weekday()]
    
    # Identificar Módulo desde la DB (Formato YYYY-MM-DD)
    fecha_iso = ahora.strftime("%Y-%m-%d")
    mod_id, mod_nombre = database_manager.obtener_modulo_por_fecha(fecha_iso)
    
    hora = ahora.time()
    bloque_actual = "A (07:45 - 09:45)"
    if datetime.time(7, 45) <= hora <= datetime.time(9, 45): bloque_actual = "A (07:45 - 09:45)"
    elif datetime.time(10, 0) <= hora <= datetime.time(12, 0): bloque_actual = "B (10:00 - 12:00)"
    elif datetime.time(12, 15) <= hora <= datetime.time(14, 15): bloque_actual = "C (12:15 - 14:15)"
    elif datetime.time(14, 30) <= hora <= datetime.time(16, 30): bloque_actual = "D (14:30 - 16:30)"
    elif datetime.time(16, 45) <= hora <= datetime.time(18, 45): bloque_actual = "E (16:45 - 18:45)"
    
    # Prevención de errores en fines de semana
    if dia_actual in ["Sábado", "Domingo"]: dia_actual = "Lunes" 
    
    return dia_actual, bloque_actual, ahora.strftime("%d/%m/%Y"), mod_id, mod_nombre

dia_hoy, bloque_hoy, fecha_hoy_str, mod_id_hoy, mod_nom_hoy = obtener_contexto_actual()

# ==========================================
# GESTIÓN DE ESTADOS
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'vista_actual' not in st.session_state:
    st.session_state.vista_actual = 'Matrices'
if 'historial_upi' not in st.session_state:
    st.session_state.historial_upi = []

def iniciar_sesion():
    if st.session_state.usuario_input and st.session_state.pass_input:
        st.session_state.autenticado = True

# ==========================================
# INTERFAZ DE LOGIN 
# ==========================================
if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col_logo, _ = st.columns([1, 0.6, 1])
    with col_logo:
        try:
            st.image("logo_upi.png", width=300)
        except:
            st.markdown("<h1 style='text-align: center;'>UPI</h1>", unsafe_allow_html=True)
            
    _, col_login, _ = st.columns([1, 0.8, 1])
    with col_login:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>Acceso al Sistema</h3>", unsafe_allow_html=True)
            st.text_input("Usuario", key="usuario_input")
            st.text_input("Contraseña", type="password", key="pass_input")
            st.button("Ingresar", type="primary", use_container_width=True, on_click=iniciar_sesion)
    st.stop()

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    try:
        st.image("logo_upi.png", width=180) 
    except:
        st.markdown("### UPI")
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.session_state.vista_actual == 'Matrices':
        st.markdown("**Horarios de Hoy**")
        opciones_horario = ["A (07:45 - 09:45)", "B (10:00 - 12:00)", "C (12:15 - 14:15)", "D (14:30 - 16:30)", "E (16:45 - 18:45)"]
        horario_visual = st.pills("Horarios", opciones_horario, default=bloque_hoy, label_visibility="collapsed", key="pills_h")
        
        bloque_db = horario_visual[0] if horario_visual else "A"
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("Buscador Avanzado", use_container_width=True, on_click=lambda: st.session_state.update({"vista_actual": "Buscador"}))
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.button("⚙️ Panel de Datos", use_container_width=True, on_click=lambda: st.session_state.update({"vista_actual": "Admin"}))
    
    elif st.session_state.vista_actual == 'Buscador':
        st.button("⬅️ Regresar a Matrices", use_container_width=True, on_click=lambda: st.session_state.update({"vista_actual": "Matrices"}))
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Historial de Búsquedas**")
        if not st.session_state.historial_upi:
            st.caption("No hay búsquedas recientes.")
        for busqueda in st.session_state.historial_upi:
            st.caption(f"• {busqueda}")
            
    elif st.session_state.vista_actual == 'Admin':
        st.button("⬅️ Regresar a Matrices", use_container_width=True, on_click=lambda: st.session_state.update({"vista_actual": "Matrices"}))

# ==========================================
# ÁREA PRINCIPAL: MATRICES (SIA)
# ==========================================
if st.session_state.vista_actual == 'Matrices':
    st.markdown(f"### 📍 Estado Actual: {dia_hoy} {fecha_hoy_str} - {mod_nom_hoy}")
    st.caption(f"Monitorización del bloque: **{horario_visual}**")
    
    estado_actual_aulas = database_manager.obtener_estado_aulas(modulo_id=mod_id_hoy, dia=dia_hoy, bloque_horario=bloque_db)
    aulas_ocupadas_total = list(estado_actual_aulas.values()).count('ocupado')
    
    c1, c2, c3 = st.columns(3)
    c1.metric(label="Ocupación Física", value=f"{aulas_ocupadas_total}/60 aulas")
    c2.metric(label="💼 Docentes Activos", value=f"{aulas_ocupadas_total}")
    c3.metric(label="Saturación", value=f"{int((aulas_ocupadas_total/60)*100)}%")
    
    st.markdown("**Leyenda:** 🔴 Ocupado | 🟢 Libre")
    col_a, _, col_b = st.columns([1, 0.05, 1])
    
    def renderizar_bloque(nombre, prefijo, estados):
        with st.container(border=True):
            st.markdown(f"#### Bloque {nombre}")
            for n in range(3):
                st.caption(f"Nivel {n+1}")
                cols = st.columns(10)
                for i in range(10):
                    nombre_aula = f"{prefijo}{n*10 + i + 1}"
                    estado = estados.get(nombre_aula, "libre")
                    color = "#ef4444" if estado == "ocupado" else "#22c55e"
                    cols[i].markdown(f"<div style='background-color:{color};padding:8px;border-radius:4px;text-align:center;color:white;font-weight:bold;font-size:0.8em;'>{nombre_aula}</div>", unsafe_allow_html=True)

    with col_a: renderizar_bloque("A", "A", estado_actual_aulas)
    with col_b: renderizar_bloque("B", "B", estado_actual_aulas)

    # BUSCADOR DE DISTANCIA (GRAFOS ESPACIALES)
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("#### ¿Cuál es el aula libre más cercana?")
        f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
        with f1: origen = st.selectbox("Mi Aula Actual", [f"A{i}" for i in range(1,31)] + [f"B{i}" for i in range(1,31)])
        with f2: cap = st.selectbox("Capacidad", ["Cualquiera", "15 Estudiantes", "30 Estudiantes"])
        with f3: tipo = st.selectbox("Tipo", ["Cualquiera", "Clase Teórica", "Laboratorio"])
        with f4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Buscar mediante Grafos 🚀", type="primary", use_container_width=True):
                candidatas = database_manager.obtener_aulas_candidatas(mod_id_hoy, dia_hoy, bloque_db, cap, tipo)
                destino, costo, ruta = grafo_espacial.dijkstra_aula_cercana(origen, candidatas)
                if destino:
                    st.success(f"🎯 **Aula más cercana: {destino}** (Costo: {costo} pts)")
                    st.caption(f"🗺️ Ruta sugerida: {' ➔ '.join(ruta)}")
                else: 
                    st.error("No hay aulas disponibles con estos requisitos.")

# ==========================================
# ÁREA PRINCIPAL: BUSCADOR AVANZADO (UPI)
# ==========================================
elif st.session_state.vista_actual == 'Buscador':
    st.header("UPI: Buscador Avanzado")
    st.caption("Manejo de horarios para planificar reuniones exitosas con el plantel docente.")
    
    with st.container(border=True):
        col_fecha, col_modulo = st.columns([1, 2])
        with col_fecha:
            fecha_sel = st.date_input("1. Fecha de la Reunión", datetime.date(2026, 4, 15))
        with col_modulo:
            st.markdown("<br>", unsafe_allow_html=True)
            # Cálculo de la fecha seleccionada
            dias_espanol = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            dia_busqueda = dias_espanol[fecha_sel.weekday()]
            mod_id_busqueda, mod_nom_busqueda = database_manager.obtener_modulo_por_fecha(fecha_sel.strftime("%Y-%m-%d"))
            
            if dia_busqueda in ["Sábado", "Domingo"]:
                st.error("⚠️ Has seleccionado un fin de semana. Por favor, elige un día hábil.")
            else:
                st.info(f"📅 **Análisis automático:** Esta fecha corresponde a un **{dia_busqueda}** del **{mod_nom_busqueda}**.")
        
        col1, col2 = st.columns(2)
        with col1:
            # Opción "Cualquiera" eliminada para forzar rigor matemático en la consulta
            horario_sel = st.selectbox("2. Bloque Horario de Inicio", ["A (07:45 - 09:45)", "B (10:00 - 12:00)", "C (12:15 - 14:15)", "D (14:30 - 16:30)", "E (16:45 - 18:45)"])
            cap_sel = st.selectbox("3. Capacidad del Aula", ["15 Estudiantes", "30 Estudiantes", "Cualquiera"])
            tipo_sel = st.selectbox("4. Tipo de Ambiente", ["Cualquiera", "Clase Teórica", "Laboratorio Computacional"])
        with col2:
            docentes_sel = st.multiselect("5. Perfil de Docentes Requeridos", ["Introductorio", "Intermedio", "Avanzado", "Especialista", "Investigación"])
            duracion_sel = st.selectbox("6. Duración de la Reunión", ["1 Bloque (2 Horas)", "2 Bloques (4 Horas)"])
            conf_sel = st.select_slider("7. Asistencia Mínima Requerida", options=["50%", "75%", "100%"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        permanencia = st.checkbox("🔒 Garantizar permanencia post-reunión (Excluir horarios donde los docentes tengan clases inmediatamente después)")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Ejecutar Motor de Búsqueda 🚀", type="primary") and dia_busqueda not in ["Sábado", "Domingo"]:
            
            # Ejecución del Backend SQL
            resultado = database_manager.ejecutar_motor_busqueda_avanzada(
                modulo_id=mod_id_busqueda,
                dia=dia_busqueda,
                bloque_inicio_str=horario_sel,
                duracion_str=duracion_sel,
                cap_str=cap_sel,
                tipo_str=tipo_sel,
                perfiles_docentes=docentes_sel,
                asistencia_str=conf_sel,
                permanencia=permanencia
            )
            
            # Actualización del historial
            resumen_busqueda = f"{fecha_sel.strftime('%d/%m/%Y')} | {horario_sel.split(' ')[0]} | Asistencia: {conf_sel}"
            st.session_state.historial_upi.insert(0, resumen_busqueda)
            
            # ==========================================
            # RENDERIZADO VISUAL DE RESULTADOS
            # ==========================================
            st.markdown("---")
            if resultado["status"] == "error":
                st.error(f"❌ {resultado['mensaje']}")
            else:
                if resultado["status"] == "success":
                    st.success(f"✅ {resultado['mensaje']}")
                else:
                    st.warning(f"⚠️ {resultado['mensaje']}")
                    
                # Visualización de Aulas
                st.markdown("#### 🏫 Espacios Físicos Viables")
                if resultado.get("aulas"):
                    cols_aulas = st.columns(6)
                    for idx, aula in enumerate(resultado["aulas"]):
                        cols_aulas[idx % 6].markdown(f"""
                        <div style='background-color:#0284c7; padding:8px; border-radius:5px; text-align:center; color:white; font-size:0.85em; font-weight:bold; margin-bottom:10px;'>
                            {aula}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No se encontraron aulas físicas disponibles.")
                
                # Visualización del Quórum Docente
                if docentes_sel:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("#### 👨‍🏫 Análisis de Quórum y Agendas")
                    st.metric("Asistencia Proyectada", f"{resultado.get('asistencia', 0)}%")
                    
                    col_ok, col_out = st.columns(2)
                    with col_ok:
                        st.success(f"Disponibles y Confirmados ({len(resultado.get('docentes_ok', []))})")
                        for d in resultado.get("docentes_ok", []):
                            st.markdown(f"- {d}")
                    with col_out:
                        st.error(f"Con Choques de Horario ({len(resultado.get('docentes_out', []))})")
                        for d in resultado.get("docentes_out", []):
                            st.markdown(f"- {d}")

# ==========================================
# ÁREA PRINCIPAL: PANEL DE ADMINISTRACIÓN (ETL)
# ==========================================
elif st.session_state.vista_actual == 'Admin':
    st.header("⚙️ Panel de Ingesta de Datos (Administración)")
    st.caption("Actualización de la base de datos central a partir de archivos Excel.")
    
    with st.container(border=True):
        st.markdown("#### 1. Descargar Plantilla Oficial")
        st.info("Utilice esta plantilla. No cambie el nombre de las pestañas ni de las columnas.")
        
        # MANEJO DE EXCEPCIONES: Evita que el servidor colapse si falta el Excel
        try:
            with open("Plantilla_Carga_UPI.xlsx", "rb") as f:
                st.download_button(
                    "📥 Descargar Plantilla_Carga_UPI.xlsx", 
                    data=f, 
                    file_name="Plantilla_Carga_UPI.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except FileNotFoundError:
            st.error("⚠️ Fallo del Sistema: El archivo base 'Plantilla_Carga_UPI.xlsx' no se encuentra en el directorio raíz del servidor. Por favor, coloque el archivo en la misma carpeta que app.py.")
        
        st.markdown("---")
        st.markdown("#### 2. Cargar Nuevos Horarios")
        st.warning("⚠️ Al procesar, se borrarán todos los datos actuales para sustituirlos por los del Excel.")
        archivo_subido = st.file_uploader("Arrastre su archivo Excel aquí", type=['xlsx'])
        
        if archivo_subido:
            if st.button("Procesar y Actualizar Base de Datos", type="primary"):
                with st.spinner("Transformando datos a SQL..."):
                    exito, mensaje = database_manager.procesar_excel_ingesta(archivo_subido)
                    if exito:
                        st.success(mensaje)
                        st.balloons()
                    else:
                        st.error(mensaje)
