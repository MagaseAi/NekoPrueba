from flask import Flask, render_template, jsonify, request
import os
import json
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

def cargar_info_mangas():
    try:
        with open("mangas.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error al cargar mangas.json: {e}")
        return {}

INFO_MANGAS = cargar_info_mangas()


def obtener_mangas():
    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix=CARPETA_BASE,
            max_results=500
        )

        mangas = set()

        for r in result.get("resources", []):
            partes = r["public_id"].split("/")
            if len(partes) > 1:
                mangas.add(partes[1])

        return sorted(list(mangas))

    except Exception as e:
        print("ERROR obtener_mangas:", e)
        return []


def obtener_caps(manga):
    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix=f"{CARPETA_BASE}/{manga}",
            max_results=500
        )

        caps = set()

        for r in result.get("resources", []):
            partes = r["public_id"].split("/")
            if len(partes) > 2:
                caps.add(partes[2])

        return sorted(list(caps))

    except Exception as e:
        print(f"ERROR obtener_caps {manga}:", e)
        return []


def obtener_imagenes(manga, cap):
    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix=f"{CARPETA_BASE}/{manga}/{cap}",
            max_results=500
        )

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
    mangas = obtener_mangas()
    print("MANGAS:", mangas)
    return render_template("main.html", mangas=mangas)


@app.route("/contacto")
def contacto():
    mangas = obtener_mangas()
    return render_template("contacto.html", mangas=mangas)


@app.route("/favoritos")
def favoritos():
    mangas = obtener_mangas()
    return render_template("favoritos.html", mangas=mangas)


@app.route("/capitulo/<manga>/<cap>")
def capitulo(manga, cap):
    return jsonify(obtener_imagenes(manga, cap))


@app.route("/manga/<manga>")
def info(manga):
    mangas = obtener_mangas()

    if manga not in mangas:
        return "Manga no encontrado", 404

    capitulos = obtener_caps(manga)

    datos = INFO_MANGAS.get(manga, {
        "titulo": manga,
        "alternativos": [],
        "mangaka": "Desconocido",
        "editorial": "Desconocida",
        "generos": "N/A",
        "estado": "N/A",
        "sinopsis": "Sin información"
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
        mangas=mangas
    )


@app.route("/manga/<manga>/<cap>")
def leer(manga, cap):
    mangas = obtener_mangas()

    if manga not in mangas:
        return "Manga no encontrado", 404

    capitulos = obtener_caps(manga)

    return render_template(
        "lector.html",
        cap=cap,
        manga=manga,
        capitulos=capitulos,
        mangas=mangas
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)