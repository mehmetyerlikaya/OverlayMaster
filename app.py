from flask import Flask, request, send_file, render_template, redirect, url_for
from PIL import Image, ImageDraw, ImageFilter
import os
from flask import send_from_directory

app = Flask(__name__)

# Route to serve files from the uploads folder
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Ensure upload folder exists
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/")
def home():
    message = request.args.get("message", "")
    error = request.args.get("error", "")
    final_image = None
    if os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], "final_image.png")):
        final_image = "/uploads/final_image.png"
    return render_template("index.html", message=message, error=error, final_image=final_image, rand=os.urandom(8).hex())

@app.route("/upload_base", methods=["POST"])
def upload_base():
    if "base_image" not in request.files or request.files["base_image"].filename == "":
        return redirect(url_for("home", error="Please select a base image."))
    file = request.files["base_image"]
    allowed_extensions = {"png", "jpg", "jpeg"}
    if "." not in file.filename or file.filename.rsplit(".", 1)[1].lower() not in allowed_extensions:
        return redirect(url_for("home", error="Invalid file type. Please upload PNG or JPG."))
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], "base.jpg")
    file.save(filepath)
    final_path = os.path.join(app.config["UPLOAD_FOLDER"], "final_image.png")
    if os.path.exists(final_path):
        os.remove(final_path)
    return redirect(url_for("home", message="Base image uploaded successfully!"))

@app.route("/apply_overlay", methods=["POST"])
def apply_overlay():
    base_img_path = os.path.join(app.config["UPLOAD_FOLDER"], "base.jpg")
    if not os.path.exists(base_img_path):
        return redirect(url_for("home", error="Please upload a base image first."))
    base_img = Image.open(base_img_path).convert("RGBA")

    if "overlay_image" not in request.files or request.files["overlay_image"].filename == "":
        return redirect(url_for("home", error="Please select an overlay image."))
    try:
        file = request.files["overlay_image"]
        overlay_img = Image.open(file).convert("RGBA")
    except Exception as e:
        return redirect(url_for("home", error=f"Error processing overlay image: {str(e)}"))

    position = request.form.get("position", "top-right")
    try:
        size = float(request.form.get("size", 0.25))
    except:
        size = 0.25
    try:
        rotation = int(request.form.get("rotation", 0))
    except:
        rotation = 0

    max_width = int(base_img.width * size)
    aspect_ratio = overlay_img.height / overlay_img.width
    new_height = int(max_width * aspect_ratio)
    overlay_img = overlay_img.resize((max_width, new_height))
    overlay_img = overlay_img.rotate(rotation, expand=True)

    positions = {
        "top-left": (50, 50),
        "top-right": (base_img.width - overlay_img.width - 50, 50),
        "bottom-left": (50, base_img.height - overlay_img.height - 50),
        "bottom-right": (base_img.width - overlay_img.width - 50, base_img.height - overlay_img.height - 50),
        "center": ((base_img.width - overlay_img.width) // 2, (base_img.height - overlay_img.height) // 2)
    }
    overlay_position = positions.get(position, positions["top-right"])

    border_size = 6
    border_color = (255, 255, 255, 180)
    bordered_overlay = Image.new("RGBA", (overlay_img.width + 2 * border_size, overlay_img.height + 2 * border_size), border_color)
    bordered_overlay.paste(overlay_img, (border_size, border_size), overlay_img)

    shadow_offset = 5
    shadow = Image.new("RGBA", bordered_overlay.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rectangle([(shadow_offset, shadow_offset), (bordered_overlay.width, bordered_overlay.height)], fill=(0, 0, 0, 100))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))

    combined_overlay = Image.alpha_composite(shadow, bordered_overlay)
    base_img.paste(combined_overlay, overlay_position, combined_overlay)

    output_path = os.path.join(app.config["UPLOAD_FOLDER"], "final_image.png")
    base_img.save(output_path, format="PNG")
    
    return redirect(url_for("home", message="Overlay applied successfully!"))

@app.route("/view_base")
def view_base():
    base_img_path = os.path.join(app.config["UPLOAD_FOLDER"], "base.jpg")
    if not os.path.exists(base_img_path):
        return "No base image uploaded yet.", 404
    return send_file(base_img_path, mimetype="image/jpeg")

@app.route("/download_final")
def download_final():
    final_img_path = os.path.join(app.config["UPLOAD_FOLDER"], "final_image.png")
    if not os.path.exists(final_img_path):
        return "No final image to download.", 404
    return send_file(final_img_path, as_attachment=True, download_name="final_image.png")

if __name__ == "__main__":
    app.run(debug=True)