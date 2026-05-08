import sqlite3

def obtener_estado_aulas(modulo_id, dia, bloque_horario):
    """
    Consulta la BD y devuelve un diccionario con el estado de las 60 aulas.
    Ejemplo de retorno: {'A1': 'ocupado', 'A2': 'libre', ...}
    """
    db_path = "simulacion_campus.db"
    
    # 1. Inicializar el universo: Asumimos que las 60 aulas están libres por defecto
    estado_aulas = {}
    for bloque in ['A', 'B']:
        for i in range(1, 31):
            estado_aulas[f"{bloque}{i}"] = "libre"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 2. Consulta SQL con JOIN: Buscamos solo las aulas que TENGAN clase en ese momento exacto
        query = """
            SELECT a.nombre
            FROM Horarios_Asignados h
            JOIN Aulas a ON h.id_aula = a.id
            WHERE h.id_modulo = ? AND h.dia = ? AND h.bloque_horario = ?
        """
        cursor.execute(query, (modulo_id, dia, bloque_horario))
        aulas_ocupadas = cursor.fetchall()

        # 3. Actualizamos el diccionario cambiando el estado a "ocupado"
        for fila in aulas_ocupadas:
            nombre_aula = fila[0] # Ej: 'A15'
            if nombre_aula in estado_aulas:
                estado_aulas[nombre_aula] = "ocupado"

        conn.close()
    except sqlite3.Error as e:
        print(f"Error crítico conectando a la BD: {e}")

    return estado_aulas
def obtener_aulas_candidatas(modulo_id, dia, bloque_horario, capacidad_str, tipo_str):
    """Devuelve una lista de nombres de aulas libres que cumplen los filtros físicos."""
    db_path = "simulacion_campus.db"
    
    # Parseo de los filtros del UI
    capacidad_req = None
    if "15" in capacidad_str: capacidad_req = 15
    elif "30" in capacidad_str: capacidad_req = 30
    
    tipo_req = None
    if "Teórica" in tipo_str: tipo_req = "Clase Teórica"
    elif "Laboratorio" in tipo_str: tipo_req = "Laboratorio"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Construcción dinámica de la consulta SQL
        query = "SELECT nombre FROM Aulas WHERE 1=1"
        params = []
        
        if capacidad_req:
            query += " AND capacidad = ?"
            params.append(capacidad_req)
        if tipo_req:
            query += " AND tipo = ?"
            params.append(tipo_req)
            
        # Filtro de exclusión: El ID del aula no debe estar en la tabla de horarios para este bloque
        query += """ AND id NOT IN (
            SELECT id_aula FROM Horarios_Asignados 
            WHERE id_modulo = ? AND dia = ? AND bloque_horario = ?
        )"""
        params.extend([modulo_id, dia, bloque_horario])
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.close()
        
        # Devolver solo los nombres en una lista plana (ej: ['A1', 'A5', 'B12'])
        return [fila[0] for fila in resultados]

    except sqlite3.Error as e:
        print(f"Error BD en búsqueda de candidatas: {e}")
        return []
def obtener_modulo_por_fecha(fecha_busqueda):
    """
    Recibe una fecha (objeto date o string YYYY-MM-DD) y devuelve el ID y Nombre del módulo.
    """
    db_path = "simulacion_campus.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        query = """
            SELECT id, nombre FROM Configuracion_Modulos 
            WHERE ? BETWEEN fecha_inicio AND fecha_fin
        """
        cursor.execute(query, (fecha_busqueda,))
        resultado = cursor.fetchone()
        conn.close()
        return resultado if resultado else (2, "Módulo 2") # Fallback por seguridad
    except Exception as e:
        print(f"Error al identificar módulo: {e}")
        return (2, "Módulo 2")
def ejecutar_motor_busqueda_avanzada(modulo_id, dia, bloque_inicio_str, duracion_str, cap_str, tipo_str, perfiles_docentes, asistencia_str, permanencia):
    """
    Motor SQL central para cruzar aulas, disponibilidad de docentes, 
    duración de la reunión y candados de permanencia.
    """
    db_path = "simulacion_campus.db"
    
    # 1. PARSEO DE PARÁMETROS LÓGICOS
    # Extraer solo la letra inicial (A, B, C, D, E)
    b_inicio = bloque_inicio_str.split(" ")[0] if bloque_inicio_str != "Cualquiera" else None
    
    secuencia_bloques = ['A', 'B', 'C', 'D', 'E']
    bloques_reunion = []
    bloque_post_reunion = None
    
    if b_inicio:
        try:
            idx_inicio = secuencia_bloques.index(b_inicio)
            duracion_bloques = 2 if "4 Horas" in duracion_str else 1
            
            # Validar que la reunión no termine después de las 18:45
            if idx_inicio + duracion_bloques > len(secuencia_bloques):
                return {"status": "error", "mensaje": "La duración solicitada excede el límite del horario de la universidad para el bloque de inicio seleccionado."}
            
            bloques_reunion = secuencia_bloques[idx_inicio : idx_inicio + duracion_bloques]
            
            # Calcular el bloque post-reunión para el Candado de Permanencia
            if permanencia and (idx_inicio + duracion_bloques < len(secuencia_bloques)):
                bloque_post_reunion = secuencia_bloques[idx_inicio + duracion_bloques]
                
        except ValueError:
            return {"status": "error", "mensaje": "Bloque de inicio no reconocido."}
    
    # Parseo de requerimientos físicos
    cap_req = 15 if "15" in cap_str else (30 if "30" in cap_str else None)
    tipo_req = "Laboratorio" if "Laboratorio" in tipo_str else ("Clase Teórica" if "Teórica" in tipo_str else None)
    asistencia_minima = int(asistencia_str.replace("%", ""))

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # ==========================================
        # FASE 1: BÚSQUEDA DE AULAS VIABLES
        # ==========================================
        query_aulas = "SELECT nombre, capacidad, tipo FROM Aulas WHERE 1=1"
        params_aulas = []
        
        if cap_req:
            query_aulas += " AND capacidad >= ?"
            params_aulas.append(cap_req)
        if tipo_req:
            query_aulas += " AND tipo = ?"
            params_aulas.append(tipo_req)
            
        if bloques_reunion:
            marcadores_bloques = ",".join(["?"] * len(bloques_reunion))
            query_aulas += f""" AND id NOT IN (
                SELECT id_aula FROM Horarios_Asignados 
                WHERE id_modulo = ? AND dia = ? AND bloque_horario IN ({marcadores_bloques})
            )"""
            params_aulas.extend([modulo_id, dia])
            params_aulas.extend(bloques_reunion)
            
        cursor.execute(query_aulas, params_aulas)
        aulas_disponibles = [f"{fila[0]} (Cap: {fila[1]})" for fila in cursor.fetchall()]
        
        if not aulas_disponibles:
            conn.close()
            return {"status": "warning", "mensaje": "No hay aulas físicas disponibles que cumplan los requisitos de espacio y tiempo."}

        # ==========================================
        # FASE 2: ANÁLISIS DE QUÓRUM DOCENTE
        # ==========================================
        if not perfiles_docentes:
             # Si la secretaria no filtró docentes, devolvemos éxito solo con aulas
             conn.close()
             return {
                 "status": "success", "mensaje": "Búsqueda de espacios completada (Sin filtro docente).",
                 "aulas": aulas_disponibles, "docentes_ok": [], "docentes_out": [], "asistencia": 100.0
             }

        # Obtener todos los docentes del perfil solicitado
        marcadores_perfiles = ",".join(["?"] * len(perfiles_docentes))
        cursor.execute(f"SELECT id, nombre, categoria FROM Docentes WHERE categoria IN ({marcadores_perfiles})", perfiles_docentes)
        docentes_target = cursor.fetchall() # Lista de tuplas (id, nombre, categoria)
        
        if not docentes_target:
             conn.close()
             return {"status": "error", "mensaje": "No existen docentes registrados con esos perfiles."}

        # Determinar qué bloques revisar para los docentes
        # (Bloques de la reunión + Bloque extra si hay candado de permanencia)
        bloques_a_evaluar_docentes = list(bloques_reunion)
        if bloque_post_reunion:
            bloques_a_evaluar_docentes.append(bloque_post_reunion)

        # Identificar qué docentes ESTÁN OCUPADOS en los bloques críticos
        marcadores_b_doc = ",".join(["?"] * len(bloques_a_evaluar_docentes))
        query_docentes_ocupados = f"""
            SELECT DISTINCT id_docente FROM Horarios_Asignados
            WHERE id_modulo = ? AND dia = ? AND bloque_horario IN ({marcadores_b_doc})
        """
        params_doc = [modulo_id, dia] + bloques_a_evaluar_docentes
        
        cursor.execute(query_docentes_ocupados, params_doc)
        ids_ocupados = set([fila[0] for fila in cursor.fetchall()])
        
        # Clasificar docentes
        docentes_ok = []
        docentes_out = []
        
        for d_id, d_nombre, d_cat in docentes_target:
            etiqueta = f"{d_nombre} ({d_cat})"
            if d_id in ids_ocupados:
                docentes_out.append(etiqueta)
            else:
                docentes_ok.append(etiqueta)

        # Calcular Quórum
        total_requeridos = len(docentes_target)
        total_disponibles = len(docentes_ok)
        porcentaje_logrado = (total_disponibles / total_requeridos) * 100 if total_requeridos > 0 else 0

        conn.close()

        # ==========================================
        # FASE 3: EVALUACIÓN DE ÉXITO O FRACASO
        # ==========================================
        if porcentaje_logrado >= asistencia_minima:
            return {
                "status": "success",
                "mensaje": "Se ha encontrado una configuración óptima.",
                "aulas": aulas_disponibles,
                "docentes_ok": docentes_ok,
                "docentes_out": docentes_out,
                "asistencia": round(porcentaje_logrado, 1)
            }
        else:
            return {
                "status": "warning",
                "mensaje": f"El cruce de horarios no alcanza el quórum. Se requiere {asistencia_minima}%, pero solo se alcanza {round(porcentaje_logrado, 1)}%.",
                "aulas": aulas_disponibles,
                "docentes_ok": docentes_ok,
                "docentes_out": docentes_out,
                "asistencia": round(porcentaje_logrado, 1)
            }

    except sqlite3.Error as e:
        return {"status": "error", "mensaje": f"Error crítico en el motor de base de datos: {e}"}
    
import pandas as pd

def procesar_excel_ingesta(archivo_excel):
    """
    Lee el Excel de la secretaria y reconstruye las tablas de la BD.
    Realiza un mapeo de nombres a IDs automáticamente.
    """
    db_path = "simulacion_campus.db"
    try:
        # 1. Leer todas las hojas
        df_modulos = pd.read_excel(archivo_excel, sheet_name='Configuracion_Modulos')
        df_aulas = pd.read_excel(archivo_excel, sheet_name='Aulas')
        df_docentes = pd.read_excel(archivo_excel, sheet_name='Docentes')
        df_horarios = pd.read_excel(archivo_excel, sheet_name='Horarios')

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 2. Limpiar tablas actuales (Traspaso total)
        cursor.executescript("DELETE FROM Horarios_Asignados; DELETE FROM Docentes; DELETE FROM Aulas; DELETE FROM Configuracion_Modulos;")

        # 3. Insertar Módulos
        for _, row in df_modulos.iterrows():
            cursor.execute("INSERT INTO Configuracion_Modulos (nombre, fecha_inicio, fecha_fin) VALUES (?,?,?)", 
                           (row['Nombre'], str(row['Fecha_Inicio']), str(row['Fecha_Fin'])))
        
        # 4. Insertar Aulas
        for _, row in df_aulas.iterrows():
            cursor.execute("INSERT INTO Aulas (nombre, capacidad, tipo) VALUES (?,?,?)", 
                           (row['Nombre'], row['Capacidad'], row['Tipo']))
            
        # 5. Insertar Docentes
        for _, row in df_docentes.iterrows():
            cursor.execute("INSERT INTO Docentes (nombre, categoria) VALUES (?,?)", 
                           (row['Nombre'], row['Categoria']))

        conn.commit()

        # 6. Mapeo de Nombres a IDs para la tabla Horarios (Crucial para integridad)
        # Recuperamos los IDs recién creados
        map_aulas = {n: i for i, n in cursor.execute("SELECT id, nombre FROM Aulas").fetchall()}
        map_docentes = {n: i for i, n in cursor.execute("SELECT id, nombre FROM Docentes").fetchall()}
        map_mods = {n: i for i, n in cursor.execute("SELECT id, nombre FROM Configuracion_Modulos").fetchall()}

        # 7. Insertar Horarios cruzando los mapas
        for _, row in df_horarios.iterrows():
            id_a = map_aulas.get(row['Nombre_Aula'])
            id_d = map_docentes.get(row['Nombre_Docente'])
            id_m = map_mods.get(row['Nombre_Modulo'])
            
            if id_a and id_d and id_m:
                cursor.execute("INSERT INTO Horarios_Asignados (id_aula, id_docente, dia, bloque_horario, id_modulo) VALUES (?,?,?,?,?)",
                               (id_a, id_d, row['Dia'], row['Bloque'], id_m))

        conn.commit()
        conn.close()
        return True, "Base de datos actualizada con éxito desde el Excel."
    except Exception as e:
        return False, f"Error al procesar el Excel: {str(e)}"