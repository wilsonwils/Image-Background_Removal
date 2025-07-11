import os
from flask import Flask, render_template, request, send_file
from PIL import Image
from transparent_background import Remover
from zipfile import ZipFile
import io


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

remover = Remover()

def center_image(result_img, canvas_size=(512, 512)):
    result_img = result_img.convert("RGBA")
    alpha = result_img.getchannel('A')
    bbox = alpha.getbbox()

    if bbox:
        cropped = result_img.crop(bbox)
    else:
        cropped = result_img

    # Resize if object is larger than canvas
    if cropped.width > canvas_size[0] or cropped.height > canvas_size[1]:
        cropped.thumbnail(canvas_size, Image.Resampling.LANCZOS)


    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    x = (canvas_size[0] - cropped.width) // 2
    y = (canvas_size[1] - cropped.height) // 2
    canvas.paste(cropped, (x, y), cropped)
    return canvas

@app.route('/', methods=['GET', 'POST'])
def upload_images():
    if request.method == 'POST':
        files = request.files.getlist('images')
        rotation_angle = int(request.form.get('rotation', 0))
        processed_filenames = []

        for file in files:
            if file and file.filename:
                img = Image.open(file.stream).convert('RGB')
                result = remover.process(img)

                # Handle result type
                if isinstance(result, Image.Image):
                    result_img = result
                else:
                    result_img = Image.fromarray(result, mode='RGBA')

                # Center the object
                centered_img = center_image(result_img)

                # Rotate if needed
                rotated_img = centered_img.rotate(rotation_angle, expand=True)

                # Save final image
                base_name = os.path.basename(file.filename)
                processed_name = os.path.splitext(base_name)[0] + '.png'
                processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_name)
                rotated_img.save(processed_path)
                processed_filenames.append(processed_name)

        return render_template('processed.html', filenames=processed_filenames)

    return render_template('upload.html')

@app.route('/processed/<filename>')
def processed_file(filename):
    return send_file(os.path.join(app.config['PROCESSED_FOLDER'], filename), mimetype='image/png')
@app.route('/download_all')
def download_all():
    zip_stream = io.BytesIO()

    with ZipFile(zip_stream, 'w') as zipf:
        for filename in os.listdir(app.config['PROCESSED_FOLDER']):
            file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
            zipf.write(file_path, arcname=filename)

    zip_stream.seek(0)
    return send_file(zip_stream, mimetype='application/zip', as_attachment=True, download_name='processed_images.zip')  

if __name__ == '__main__':
    app.run(debug=True)
