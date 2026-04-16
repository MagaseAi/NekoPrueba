from flask import Flask, render_template, jsonify, request
import os
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import cloudinary
import cloudinary.api

load_dotenv()

app = Flask(__name__)

cloudinary.config(
    cloud_name=os.environ.get("CLOUD_NAME"),
    api_key=os.environ.get("API_KEY"),
    api_secret=os.environ.get("API_SECRET"),
    secure=True
)

CARPETA_BASE = "mangas"
MINUTOS_NOVEDAD = 1  # Cambiar a 2160 para 36 horas

def cargar_info_mangas():
    try:
        with open("mangas.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error al cargar mangas.json: {e}")
        return {}

INFO_MANGAS = cargar_info_mangas()


def es_reciente(fecha_str):
    try:
        fecha = datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
        ahora = datetime.now(timezone.utc)
        diferencia = ahora - fecha
        return diferencia < timedelta(minutes=MINUTOS_NOVEDAD)
    except Exception as e:
        print(f"Error en es_reciente: {e}")
        return False


def obtener_novedades_manga(manga, capitulos):
    try:
        if not capitulos:
            return None, None
        
        total_caps = len(capitulos)
        caps_recientes = []
        
        for cap in capitulos:
            ruta = f"{CARPETA_BASE}/{manga}/{cap}"
            try:
                result = cloudinary.api.resources_by_asset_folder(
                    asset_folder=ruta,
                    max_results=1
                )
                
                recursos = result.get("resources", [])
                if recursos:
                    fecha = recursos[0].get("created_at", "")
                    if es_reciente(fecha):
                        caps_recientes.append(cap)
            except:
                continue
        
        print(f"DEBUG {manga}: total_caps={total_caps}, caps_recientes={len(caps_recientes)}, lista={caps_recientes}")
        
        if len(caps_recientes) == 0:
            return None, None
        
        if total_caps == 1 and len(caps_recientes) == 1:
            return "manga_nuevo", None
        
        if len(caps_recientes) < total_caps:
            return "cap_nuevo", caps_recientes[-1]
        
        if total_caps <= 2 and len(caps_recientes) == total_caps:
            return "manga_nuevo", None
        
        return "cap_nuevo", caps_recientes[-1]
        
    except Exception as e:
        print(f"Error verificando novedades de {manga}: {e}")
        return None, None


def obtener_mangas():
    try:
        result = cloudinary.api.subfolders(CARPETA_BASE)
        print("MANGAS ENCONTRADOS:", result)
        
        mangas_emision = {}
        mangas_finalizados = {}
        
        for f in result.get("folders", []):
            nombre = f["name"]
            
            try:
                caps_result = cloudinary.api.subfolders(f"{CARPETA_BASE}/{nombre}")
                capitulos = [c["name"] for c in caps_result.get("folders", [])]
            except:
                capitulos = []
            
            tipo_novedad, cap_nuevo = obtener_novedades_manga(nombre, capitulos)
            
            es_manga_nuevo = tipo_novedad == "manga_nuevo"
            es_cap_nuevo = tipo_novedad == "cap_nuevo"
            
            if es_manga_nuevo:
                prioridad = 2
            elif es_cap_nuevo:
                prioridad = 1
            else:
                prioridad = 0
            
            info_manga = INFO_MANGAS.get(nombre, {})
            estado = info_manga.get("estado", "En emision")
            es_finalizado = estado.lower() == "finalizado"
            
            print(f"Manga: {nombre}, Estado: {estado}, Finalizado: {es_finalizado}")
            
            manga_data = {
                "titulo": nombre,
                "path": f["path"],
                "es_manga_nuevo": es_manga_nuevo,
                "es_cap_nuevo": es_cap_nuevo,
                "cap_nuevo": cap_nuevo if cap_nuevo else "",
                "prioridad": prioridad,
                "estado": estado,
                "es_finalizado": es_finalizado
            }
            
            if es_finalizado:
                mangas_finalizados[nombre] = manga_data
            else:
                mangas_emision[nombre] = manga_data
        
        mangas_emision_ordenados = dict(sorted(
            mangas_emision.items(),
            key=lambda x: x[1]["prioridad"],
            reverse=True
        ))
        
        mangas_finalizados_ordenados = dict(sorted(
            mangas_finalizados.items(),
            key=lambda x: x[1]["titulo"]
        ))
        
        return mangas_emision_ordenados, mangas_finalizados_ordenados

    except Exception as e:
        print("ERROR obtener_mangas:", e)
        return {}, {}


def obtener_caps(manga):
    try:
        result = cloudinary.api.subfolders(f"{CARPETA_BASE}/{manga}")
        print(f"CAPS DE {manga}:", result)
        return [f["name"] for f in result.get("folders", [])]

    except Exception as e:
        print(f"ERROR obtener_caps {manga}:", e)
        return []


def obtener_imagenes(manga, cap):
    try:
        ruta = f"{CARPETA_BASE}/{manga}/{cap}"
        print(f"Buscando en carpeta: {ruta}")
        
        result = cloudinary.api.resources_by_asset_folder(
            asset_folder=ruta,
            max_results=500
        )

        print(f"Imagenes encontradas: {len(result.get('resources', []))}")

        urls = []
        for r in result.get("resources", []):
            url = r["secure_url"]
            url = url.replace("/upload/", "/upload/q_auto,f_auto,w_1200/")
            urls.append(url)

        def ordenar(url):
            nombre = url.split("/")[-1].split(".")[0]
            try:
                if "_P" in nombre:
                    return int(nombre.split("_P")[-1])
                return int(nombre)
            except:
                return 9999

        urls.sort(key=ordenar)
        return urls

    except Exception as e:
        print(f"ERROR obtener_imagenes {manga}/{cap}:", e)
        return []


@app.route("/")
def main():
    mangas_emision, mangas_finalizados = obtener_mangas()
    todos_mangas = {**mangas_emision, **mangas_finalizados}
    return render_template("main.html", mangas=todos_mangas, mangas_emision=mangas_emision, mangas_finalizados=mangas_finalizados)


@app.route("/contacto")
def contacto():
    mangas_emision, mangas_finalizados = obtener_mangas()
    todos_mangas = {**mangas_emision, **mangas_finalizados}
    return render_template("contacto.html", mangas=todos_mangas)


@app.route("/favoritos")
def favoritos():
    mangas_emision, mangas_finalizados = obtener_mangas()
    todos_mangas = {**mangas_emision, **mangas_finalizados}
    return render_template("favoritos.html", mangas=todos_mangas)


@app.route("/capitulo/<manga>/<cap>")
def capitulo(manga, cap):
    return jsonify(obtener_imagenes(manga, cap))


@app.route("/manga/<manga>")
def info(manga):
    mangas_emision, mangas_finalizados = obtener_mangas()
    todos_mangas = {**mangas_emision, **mangas_finalizados}

    if manga not in todos_mangas:
        return "Manga no encontrado", 404

    capitulos = obtener_caps(manga)

    datos = INFO_MANGAS.get(manga, {
        "titulo": manga,
        "alternativos": [],
        "mangaka": "Desconocido",
        "editorial": "Desconocida",
        "generos": "N/A",
        "estado": "N/A",
        "sinopsis": "Sin informacion"
    })

    pagina = request.args.get("page", 1, type=int)
    por_pagina = 6

    inicio = (pagina - 1) * por_pagina
    fin = inicio + por_pagina

    capitulos_pagina = capitulos[inicio:fin]
    total_paginas = (len(capitulos) + por_pagina - 1) // por_pagina

    return render_template(
        "info.html",
        capitulos=capitulos_pagina,
        manga=manga,
        datos=datos,
        pagina=pagina,
        total_paginas=total_paginas,
        mangas=todos_mangas
    )


@app.route("/manga/<manga>/<cap>")
def leer(manga, cap):
    mangas_emision, mangas_finalizados = obtener_mangas()
    todos_mangas = {**mangas_emision, **mangas_finalizados}

    if manga not in todos_mangas:
        return "Manga no encontrado", 404

    capitulos = obtener_caps(manga)

    return render_template(
        "lector.html",
        cap=cap,
        manga=manga,
        capitulos=capitulos,
        mangas=todos_mangas
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)