import heapq

def construir_grafo_campus():
    """Construye el grafo espacial con 60 aulas y sus pesos de distancia."""
    grafo = {}
    aulas = [f"A{i}" for i in range(1, 31)] + [f"B{i}" for i in range(1, 31)]
    
    # Inicializar nodos
    for aula in aulas:
        grafo[aula] = {}

    # 1. Conexiones Horizontales en Pasillos (Peso = 1)
    for bloque in ['A', 'B']:
        for nivel in range(3): # Niveles 0, 1, 2 (que representan N1, N2, N3)
            offset = nivel * 10
            for i in range(1, 10): # Conecta la 1 con la 2, 2 con 3... hasta 9 con 10
                nodo_actual = f"{bloque}{offset + i}"
                nodo_siguiente = f"{bloque}{offset + i + 1}"
                grafo[nodo_actual][nodo_siguiente] = 1
                grafo[nodo_siguiente][nodo_actual] = 1

    # 2. Conexiones Verticales - Escaleras (Peso = 3)
    # Ubicadas en el centro (aulas terminadas en 5 y 6)
    for bloque in ['A', 'B']:
        for nivel in [0, 1]: # Conecta N1 con N2, y N2 con N3
            offset_actual = nivel * 10
            offset_siguiente = (nivel + 1) * 10
            
            # Escalera izquierda (Aula 5)
            n1_5 = f"{bloque}{offset_actual + 5}"
            n2_5 = f"{bloque}{offset_siguiente + 5}"
            grafo[n1_5][n2_5] = 3
            grafo[n2_5][n1_5] = 3
            
            # Escalera derecha (Aula 6)
            n1_6 = f"{bloque}{offset_actual + 6}"
            n2_6 = f"{bloque}{offset_siguiente + 6}"
            grafo[n1_6][n2_6] = 3
            grafo[n2_6][n1_6] = 3

    # 3. Conexiones de Transición entre Edificios (Peso = 5)
    # Asumimos que se cruza por la planta baja (Nivel 1) en el centro
    grafo['A5']['B5'] = 5
    grafo['B5']['A5'] = 5
    grafo['A6']['B6'] = 5
    grafo['B6']['A6'] = 5
    
    return grafo

def dijkstra_aula_cercana(origen, aulas_candidatas):
    """Encuentra el aula libre más cercana usando el algoritmo de Dijkstra."""
    grafo = construir_grafo_campus()
    
    if origen in aulas_candidatas:
        return origen, 0, [origen] # ¡Estás en un aula que ya cumple los requisitos!
        
    distancias = {nodo: float('inf') for nodo in grafo}
    distancias[origen] = 0
    padres = {nodo: None for nodo in grafo}
    cola_prioridad = [(0, origen)] # (distancia_acumulada, nodo)
    
    while cola_prioridad:
        dist_actual, nodo_actual = heapq.heappop(cola_prioridad)
        
        # Como Dijkstra procesa siempre el camino más corto primero,
        # la primera aula candidata que extraigamos ES la más cercana de todo el campus.
        if nodo_actual in aulas_candidatas:
            # Reconstruir el camino de regreso
            camino = []
            temp = nodo_actual
            while temp is not None:
                camino.append(temp)
                temp = padres[temp]
            return nodo_actual, dist_actual, camino[::-1]
            
        if dist_actual > distancias[nodo_actual]:
            continue
            
        for vecino, peso in grafo[nodo_actual].items():
            nueva_dist = dist_actual + peso
            if nueva_dist < distancias[vecino]:
                distancias[vecino] = nueva_dist
                padres[vecino] = nodo_actual
                heapq.heappush(cola_prioridad, (nueva_dist, vecino))
                
    return None, float('inf'), []