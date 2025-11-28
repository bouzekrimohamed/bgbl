import os
import tempfile
import subprocess
import threading
import time
import webbrowser
import sys
import shutil

from flask import Flask, request, jsonify
from flask_cors import CORS
import paramiko

# ======================================================
# 💡 Configuration SFTP (Prod)
# ======================================================
SFTP_CONFIG = {
    "host": "mft-int.int.kn",
    "port": 22,
    "username": "esr_multiclient",
    "password": "*Esr2024!",
    "remote_dir": "/pub/inbound"
}

# ======================================================
# 🚀 Serveur Flask intégré
# ======================================================
app = Flask(__name__)
CORS(app)

@app.route("/upload", methods=["POST"])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "Aucun fichier reçu"}), 400

        f = request.files["file"]
        filename = f.filename or "unknown.csv"

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            f.save(tmp.name)
            local_path = tmp.name

        print(f"📂 Fichier reçu : {filename} ({os.path.getsize(local_path)} octets)")
        print("🔌 Connexion SFTP en cours...")

        transport = paramiko.Transport((SFTP_CONFIG["host"], SFTP_CONFIG["port"]))
        transport.connect(
            username=SFTP_CONFIG["username"],
            password=SFTP_CONFIG["password"]
        )
        sftp = paramiko.SFTPClient.from_transport(transport)

        try:
            sftp.chdir(SFTP_CONFIG["remote_dir"])
        except IOError:
            sftp.close()
            transport.close()
            return jsonify({"status": "error", "message": f"Dossier distant introuvable : {SFTP_CONFIG['remote_dir']}"}), 500

        remote_path = os.path.join(SFTP_CONFIG["remote_dir"], filename)
        print(f"⬆️  Envoi du fichier vers {remote_path} ...")

        sftp.put(local_path, remote_path)
        sftp.close()
        transport.close()
        os.remove(local_path)

        print("✅ Fichier envoyé avec succès !")
        return jsonify({"status": "success", "message": f"Fichier envoyé sur le SFTP : {filename}"})

    except Exception as e:
        print("❌ Erreur :", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


# ======================================================
# 🧠 Fonction utilitaire PyInstaller
# ======================================================
def resource_path(relative_path):
    """Permet d’accéder aux ressources même dans un .exe"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ======================================================
# 🪟 Popup de confirmation (affichée même si les notifs Windows sont bloquées)
# ======================================================
def show_popup():
    try:
        import tkinter as tk
        from PIL import Image, ImageTk
    except ImportError:
        print("Tkinter ou Pillow non disponible pour la popup.")
        return

    root = tk.Tk()
    root.title("BigBlue ESR_ST")
    root.geometry("380x130")
    root.resizable(False, False)
    root.attributes('-topmost', True)
    root.configure(bg="#ffffff")

    # Logo KN si présent
    icon_path = resource_path("kn.ico")
    try:
        img = Image.open(icon_path)
        img = img.resize((48, 48))
        icon = ImageTk.PhotoImage(img)
        lbl_icon = tk.Label(root, image=icon, bg="#ffffff")
        lbl_icon.image = icon
        lbl_icon.pack(side="left", padx=15, pady=15)
    except Exception:
        pass

    lbl_text = tk.Label(
        root,
        text="✅ Serveur BigBlue lancé avec succès !\nL’outil est prêt à l’emploi.",
        font=("Segoe UI", 10),
        bg="#ffffff",
        justify="left"
    )
    lbl_text.pack(side="left", padx=10)

    # Fermeture automatique après 3 s
    root.after(3000, root.destroy)
    root.mainloop()


# ======================================================
# 🧩 Fonction principale
# ======================================================
def run_flask():
    app.run(port=5000, debug=False, use_reloader=False)


def main():
    print("🚀 Lancement du serveur BigBlue...")

    # Lancer le serveur Flask en arrière-plan
    threading.Thread(target=run_flask, daemon=True).start()

    # Attendre qu’il démarre
    time.sleep(3)

    # Ouvrir automatiquement le site GitHub hébergé
    webbrowser.open("https://bouzekrimohamed.github.io/bgbl/")

    # Notification système (si win10toast dispo)
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        icon_path = resource_path("kn.ico") if os.path.exists(resource_path("kn.ico")) else None
        toaster.show_toast(
            "BigBlue – ESR_ST",
            "✅ Serveur SFTP lancé avec succès.\nL’outil est prêt à l’emploi !",
            icon_path=icon_path,
            duration=5,
            threaded=True,
        )
    except Exception:
        pass

    # Toujours afficher la popup visible
    threading.Thread(target=show_popup, daemon=True).start()

    print("✅ Serveur prêt. Ne fermez pas le programme tant que vous utilisez l’outil.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Arrêt demandé par l’utilisateur.")

    # Nettoyage silencieux
    try:
        tempdir = getattr(sys, '_MEIPASS', tempfile.gettempdir())
        shutil.rmtree(tempdir, ignore_errors=True)
    except Exception:
        pass

@app.route("/download-metabase")
def download_metabase():
    import requests
    url = "https://metabase.internal.bigblue.co/api/public/card/bb321409-6274-4e49-a7c6-1848485711fb/query/xlsx?parameters=%5B%7B%22id%22%3A%22083183ed-2e25-4369-a038-3018b590dd20%22%2C%22value%22%3Anull%7D%2C%7B%22id%22%3A%22f38e5c5b-8834-48a1-a796-a8220fab3080%22%2C%22value%22%3Anull%7D%2C%7B%22id%22%3A%22333ac6b7-3aa3-4b6e-bc96-83864304c937%22%2C%22value%22%3Anull%7D%5D"
    
    try:
        print("Téléchargement du stock depuis Metabase...")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        
        return Response(
            r.content,
            headers={
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Content-Disposition": "attachment; filename=Stock_BGB.xlsx"
            }
        )
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    main()
