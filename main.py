from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import re
import shutil

app = FastAPI()

# Crear carpetas necesarias automáticamente
os.makedirs("data", exist_ok=True)
os.makedirs("static/logos", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Inicializar archivos base solo si no existen
if not os.path.exists("data/logo.txt"):
    with open("data/logo.txt", "w", encoding="utf-8") as f:
        f.write('#EXTM3U\n')
        f.write('#EXTINF:-1 tvg-id="CanalC.ve" tvg-name="Canal C del Zulia" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/4/43/Canal_C_del_Zulia.png" group-title="Entretenimiento", Canal C del Zulia\n')
        f.write('#EXTINF:-1 tvg-id="Globovision.ve" tvg-name="Globovisión" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/c/c0/Logo-Globovisi%C3%B3n.png" group-title="Noticias", Globovisión\n')
        f.write('#EXTINF:-1 tvg-id="AguacateTV.ve" tvg-name="Aguacate TV" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/1/14/No_Image_Available.jpg" group-title="Entretenimiento", Aguacate TV\n')

if not os.path.exists("data/transmisiones.txt"):
    with open("data/transmisiones.txt", "w", encoding="utf-8") as f:
        f.write('#EXTM3U\n')
        f.write('#EXTINF:-1 tvg-id="CanalC.ve", Canal C del Zulia\nhttps://cristianbracho900-ranking-20.hf.space/hls/index.m3u8\n')
        f.write('#EXTINF:-1 tvg-id="Globovision.ve", Globovisión\nhttps://backup.thundernet.streampool.net/10323/live/hls/globovisionsd/1920_1080_3000_128/index_824.m3u8\n')
        f.write('#EXTINF:-1 tvg-id="AguacateTV.ve", Aguacate TV\nhttps://streamtv.intervenhosting.net:3040/hybrid/play.m3u8\n')

if not os.path.exists("data/history-tv.txt"):
    with open("data/history-tv.txt", "w", encoding="utf-8") as f:
        f.write('[CANAL]\nid=CanalC.ve\ncountry=Estado Zulia, Venezuela\nfundacion=23 de abril de 2024\npropietario=Cristian Bracho\nmedio=Streaming\neslogan=Cultura regional\ndescription=Canal C del Zulia es una televisora digital zuliana.\n\n[CANAL]\nid=Globovision.ve\ncountry=Caracas, Venezuela\nfundacion=1 de diciembre de 1994\npropietario=Raúl Gorrín\nmedio=Noticias\neslogan="Información responsable y veraz"\ndescription=Cadena de noticias de Venezuela.\n\n[CANAL]\nid=AguacateTV.ve\ncountry=Barquisimeto, Venezuela\nfundacion=No registrada\npropietario=Desconocido\nmedio=IPTV\neslogan="Una nueva forma de comunicar"\ndescription=Canal digital desde Barquisimeto.\n')

# Montar estáticos si la carpeta existe y tiene archivos
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

def parse_m3u_file(filepath):
    channels = {}
    if not os.path.exists(filepath): return channels
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    current_channel = None
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            id_match = re.search(r'tvg-id="([^"]+)"', line)
            name_match = re.search(r',\s*([^\n]+)', line)
            logo_match = re.search(r'tvg-logo="([^"]+)"', line)
            group_match = re.search(r'group-title="([^"]+)"', line)
            if id_match and name_match:
                tvg_id = id_match.group(1)
                current_channel = tvg_id
                channels[tvg_id] = {
                    "tvg_id": tvg_id,
                    "name": name_match.group(1).strip(),
                    "logo": logo_match.group(1) if logo_match else "https://upload.wikimedia.org/wikipedia/commons/1/14/No_Image_Available.jpg",
                    "group": group_match.group(1) if group_match else "General",
                    "url": ""
                }
        elif line and not line.startswith("#") and current_channel:
            channels[current_channel]["url"] = line
            current_channel = None
    return channels

def parse_history_file(filepath):
    histories = {}
    if not os.path.exists(filepath): return histories
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    sections = content.split("[CANAL]")
    for section in sections:
        if not section.strip(): continue
        lines = section.strip().split("\n")
        if lines[0].startswith("id="):
            tvg_id = lines[0].replace("id=", "").strip()
            data = {"tvg_id": tvg_id}
            for line in lines[1:]:
                if "=" in line:
                    key, val = line.split("=", 1)
                    data[key.strip()] = val.strip()
            histories[tvg_id] = data
    return histories

@app.get("/api/channels")
def get_channels():
    logos_data = parse_m3u_file("data/logo.txt")
    streams_data = parse_m3u_file("data/transmisiones.txt")
    histories_data = parse_history_file("data/history-tv.txt")
    final_channels = []
    for tvg_id, base_info in logos_data.items():
        stream_info = streams_data.get(tvg_id, {})
        history_info = histories_data.get(tvg_id, {})
        final_channels.append({
            "tvg_id": tvg_id,
            "name": base_info["name"],
            "logo": base_info["logo"],
            "category": base_info["group"].lower(),
            "stream": stream_info.get("url", "") if stream_info else "",
            "country": history_info.get("country", "Venezuela"),
            "fundacion": history_info.get("fundacion", "No registrada"),
            "propietario": history_info.get("propietario", "Desconocido"),
            "medio": history_info.get("medio", "Streaming Digital"),
            "eslogan": history_info.get("eslogan", ""),
            "description": history_info.get("description", "Sin descripción disponible.")
        })
    return final_channels

@app.post("/api/add-channel")
async def add_channel(
    nombre: str = Form(...), stream_url: str = Form(...), categoria: str = Form(...), calidad: str = Form(...),
    pais: str = Form(...), fundacion: str = Form(...), propietario: str = Form(...), medio: str = Form(...),
    eslogan: str = Form(...), descripcion: str = Form(...), logo_file: UploadFile = File(None), logo_url: str = Form(None)
):
    tvg_id = re.sub(r'[^a-zA-Z0-9]', '', nombre) + ".stream"
    final_logo_url = logo_url if logo_url else "https://upload.wikimedia.org/wikipedia/commons/1/14/No_Image_Available.jpg"
    
    if logo_file and logo_file.filename:
        file_path = f"static/logos/{tvg_id}_{logo_file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(logo_file.file, buffer)
        final_logo_url = f"/static/logos/{tvg_id}_{logo_file.filename}"

    with open("data/logo.txt", "a", encoding="utf-8") as f:
        f.write(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{nombre}" tvg-logo="{final_logo_url}" group-title="{categoria.capitalize()}", {nombre}\n')
    with open("data/transmisiones.txt", "a", encoding="utf-8") as f:
        f.write(f'#EXTINF:-1 tvg-id="{tvg_id}", {nombre} ({calidad})\n{stream_url}\n')
    with open("data/history-tv.txt", "a", encoding="utf-8") as f:
        f.write(f"\n[CANAL]\nid={tvg_id}\ncountry={pais}\nfundacion={fundacion}\npropietario={propietario}\nmedio={medio}\neslogan={eslogan}\ndescription={descripcion}\n")
    return JSONResponse(content={"message": "OK"})

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
