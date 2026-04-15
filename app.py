from flask import Flask, render_template, jsonify, request
import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.api

load_dotenv()

app = Flask(__name__) 


cloudinary.config(
    cloud_name=os.environ.get("CLOUD_NAME"),
    api_key=os.environ.get("API_KEY"),
    api_secret=os.environ.get("API_SECRET")
)

CARPETA_BASE = "mangas"


def obtener_mangas():
    result = cloudinary.api.subfolders(CARPETA_BASE)
    print("MANGAS ENCONTRADOS:", result)  # 🔥 DEBUG
    return [f["name"] for f in result.get("folders", [])]


def obtener_caps(manga):
    result = cloudinary.api.subfolders(f"{CARPETA_BASE}/{manga}")
    print(f"CAPS DE {manga}:", result)  # 🔥 DEBUG
    return [f["name"] for f in result.get("folders", [])]


def obtener_imagenes(manga, cap):
    result = cloudinary.api.resources(
        type="upload",
        prefix=f"{CARPETA_BASE}/{manga}/{cap}",
        max_results=500
    )

    print(f"IMÁGENES DE {manga}/{cap}:", result)  # 🔥 DEBUG

    urls = [r["secure_url"] for r in result.get("resources", [])]

    def ordenar(url):
        nombre = url.split("/")[-1].split(".")[0]
        try:
            return int(nombre)
        except:
            return 9999

    urls.sort(key=ordenar)
    return urls


# =========================
# 🔥 RUTAS
# =========================

@app.route("/")
def main():
    mangas = obtener_mangas()
    return render_template("main.html", mangas=mangas)


@app.route("/contacto")
def contacto():
    mangas = obtener_mangas()
    return render_template("contacto.html", mangas=mangas)


@app.route("/favoritos")
def favoritos():
    mangas = obtener_mangas()
    return render_template("favoritos.html", mangas=mangas)


@app.route("/<manga>")
def info(manga):
    mangas = obtener_mangas()
    print("LISTA MANGAS:", mangas)  # 🔥 DEBUG

    if manga not in mangas:
        print("NO ENCONTRADO:", manga)  # 🔥 DEBUG
        return "Manga no encontrado", 404

    capitulos = obtener_caps(manga)

    datos = {
        "titulo": manga,
        "alternativos": [],
        "mangaka": "Desconocido",
        "editorial": "Desconocida",
        "generos": "N/A",
        "estado": "N/A",
        "sinopsis": "Sin información"
    }

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


@app.route("/<manga>/<cap>")
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


@app.route("/capitulo/<manga>/<cap>")
def capitulo(manga, cap):
    return jsonify(obtener_imagenes(manga, cap))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)