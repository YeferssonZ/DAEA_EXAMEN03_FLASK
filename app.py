from flask import Flask, request, jsonify
import requests
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

# Función para obtener datos de la API de películas
def obtener_peliculas():
    url_peliculas = "http://192.168.1.106:5283/api/pelicula"
    response = requests.get(url_peliculas)
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        return None

# Función para obtener datos de la API de géneros
def obtener_generos():
    url_generos = "http://192.168.1.106:5283/api/genero"
    response = requests.get(url_generos)
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        return None

# Función para obtener datos de la API de calificaciones
def obtener_calificaciones():
    url_calificaciones = "http://192.168.1.106:5283/api/rating"
    response = requests.get(url_calificaciones)
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        return None

# Codificación de los géneros de las películas usando one-hot encoding
def codificar_generos(peliculas, generos):
    genero_dict = {genero['nombre']: i for i, genero in enumerate(generos)}
    for pelicula in peliculas:
        generos_pelicula = pelicula['generos']
        generos_encoded = [0] * len(generos)
        for genero in generos_pelicula:
            genero_nombre = genero['nombre']
            if genero_nombre in genero_dict:
                genero_index = genero_dict[genero_nombre]
                generos_encoded[genero_index] = 1
        pelicula['generos_encoded'] = generos_encoded

# Función para calcular la similitud entre películas
def calcular_similitud_entre_peliculas(pelicula_1, pelicula_2):
    return cosine_similarity([pelicula_1], [pelicula_2])[0][0]

# Función para recomendar películas similares a una película dada
def recomendar_peliculas_similares(peliculas, calificaciones, usuario_id):
    # Obtener las calificaciones del usuario
    calificaciones_usuario = [cal for cal in calificaciones if cal['usuarioId'] == usuario_id]

    if len(calificaciones_usuario) < 2:
        return None

    # Obtener las dos últimas calificaciones del usuario (asumiendo que están ordenadas por llegada)
    ultima_calificacion = calificaciones_usuario[-1]
    penultima_calificacion = calificaciones_usuario[-2]

    # Obtener las películas correspondientes a estas calificaciones
    pelicula_ultima = next((p for p in peliculas if p['id'] == ultima_calificacion['peliculaId']), None)
    pelicula_penultima = next((p for p in peliculas if p['id'] == penultima_calificacion['peliculaId']), None)

    if not pelicula_ultima or not pelicula_penultima:
        return None

    # Determinar la película de referencia basada en la calificación más alta
    if ultima_calificacion['calificacion'] >= penultima_calificacion['calificacion']:
        pelicula_referencia = pelicula_ultima
    else:
        pelicula_referencia = pelicula_penultima

    # Calcular la similitud de todas las demás películas con la película de referencia
    similitudes = []
    for otra_pelicula in peliculas:
        if otra_pelicula['id'] != pelicula_referencia['id']:
            similitud = calcular_similitud_entre_peliculas(pelicula_referencia['generos_encoded'], otra_pelicula['generos_encoded'])
            similitudes.append((otra_pelicula, similitud))

    similitudes.sort(key=lambda x: x[1], reverse=True)

    # Filtrar películas ya calificadas por el usuario
    peliculas_calificadas_por_usuario = {calificacion['peliculaId'] for calificacion in calificaciones if calificacion['usuarioId'] == usuario_id}
    for pelicula, similitud in similitudes:
        if pelicula['id'] not in peliculas_calificadas_por_usuario:
            return pelicula

    return None

@app.route('/recomendar/<usuario_id>', methods=['GET'])
def recomendar_peliculas(usuario_id):
    # Obtener datos de las APIs
    peliculas = obtener_peliculas()
    generos = obtener_generos()
    calificaciones = obtener_calificaciones()

    if peliculas and generos and calificaciones:
        # Codificar los géneros de las películas utilizando one-hot encoding
        codificar_generos(peliculas, generos)

        # Recomendar una película similar basada en las dos últimas calificaciones del usuario
        pelicula_recomendada = recomendar_peliculas_similares(peliculas, calificaciones, usuario_id)

        if pelicula_recomendada:
            pelicula_data = {
                'id': pelicula_recomendada['id'],
                'titulo': pelicula_recomendada['titulo'],
                'videoUrl': pelicula_recomendada['videoUrl'],
                'generos': pelicula_recomendada['generos']
            }
            return jsonify({'pelicula_recomendada': pelicula_data})
        else:
            return jsonify({'error': 'No se pudo encontrar una película recomendada'})
    else:
        return jsonify({'error': 'No se pudieron obtener datos de las APIs'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=4000)
