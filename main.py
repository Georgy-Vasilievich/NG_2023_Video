from mail import send_email
from flask import Flask, abort, render_template, redirect, request, url_for
from PIL import Image
from proglog import ProgressBarLogger
import os
import uuid

import moviepy.editor as moviepy

app = Flask(__name__)

ALLOWED_UPLOAD_EXTENSIONS = {'mp4', 'webm', 'mkv', 'avi', 'ogv'}
ALLOWED_CONVERT_EXTENSIONS = {'mp4', 'webm', 'mkv', 'avi', 'ogv', 'ogg', 'mp3', 'flac'}
AUDIO_EXTENSIONS = {'ogg', 'mp3', 'flac'}
ALLOWED_WATERMARK_EXTENSIONS = {'bmp', 'png', 'jpg', 'jpeg', 'tiff', 'tga', 'svg'}

percentages = {}

class BarLogger(ProgressBarLogger):
    global percentages
    id = None

    def bars_callback(self, bar, attr, value, old_value=None):
        percentages[self.id] = (value / self.bars[bar]['total']) * 100

    def __init__(self, id):
        super(self.__class__, self).__init__()
        self.id = id

def is_integer(n):
    try:
        return float(n).is_integer()
    except ValueError:
        return False

def getExtension(filename, isWatermark=False):
    if not '.' in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    if extension in ALLOWED_UPLOAD_EXTENSIONS and not isWatermark:
        return extension
    elif extension in ALLOWED_WATERMARK_EXTENSIONS and isWatermark:
        return extension
    else:
        return False

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST' and 'video' in request.files:
        file = request.files['video']
        if not file.filename == '':
            extension = getExtension(file.filename)
            if extension != False:
                filename = str(uuid.uuid4()) + '.' + extension
                file.save(os.path.join('videos', filename))
                return redirect(url_for('video', id=filename))
        else:
            return render_template('index.html', error='Non-allowed file extension.')

    return render_template('index.html')

@app.route('/video', methods=['GET', 'POST'])
def video():
    error = ''
    changed = False
    audio = None
    id = request.args.get('id')
    path = os.path.join('videos', id)
    if id != None and os.path.isfile(path):
        clip = moviepy.VideoFileClip(path)
        if request.method == 'POST':
            start = request.form.get('start')
            end = request.form.get('end')
            extension = request.form.get('extension')
            email = request.form.get('email')
            if not email:
                abort(400)
            if start and end:
                if is_integer(start) and is_integer(end) and int(start) < int(end):
                    if int(start) < 0 or int(end) > clip.duration:
                        error += 'Selected subclip out of bounds.<br>'
                    else:
                        clip = clip.subclip(start, end)
                        changed = True
            if extension:
                if extension in ALLOWED_CONVERT_EXTENSIONS:
                    if extension in AUDIO_EXTENSIONS:
                        audio = clip.audio
                    newId = id.rsplit('.', 1)[0] + '.' + extension
                    if id == newId:
                        error += 'A different extension than the currently used one is needed.<br>'
                    else:
                        changed = True
                else:
                    error += 'Requested recode extension not allowed.<br>'
            if 'watermark' in request.files:
                file = request.files['watermark']
                if not file.filename == '':
                    if audio:
                        error += 'Audio cannot be watermarked.<br>'
                    else:
                        watermarkExtension = getExtension(file.filename, True)
                        if watermarkExtension:
                            watermarkPath = os.path.join('videos', id + '-watermark' + '.' + watermarkExtension)
                            file.save(watermarkPath)

                            formatter = {'PNG': 'RGBA', 'JPEG': 'RGB'}
                            img = Image.open(watermarkPath)
                            rgbimg = Image.new(formatter.get(img.format, 'RGB'), img.size)
                            rgbimg.paste(img)
                            rgbimg.save(watermarkPath, format=img.format)

                            watermark = (moviepy.ImageClip(watermarkPath)
                                .set_duration(clip.duration)
                                .set_pos(('right', 'bottom')))

                            clip = moviepy.CompositeVideoClip([clip, watermark])
                            os.remove(watermarkPath)
                            changed = True
                        else:
                            error += 'Non-allowed watermark extension.<br>'
            if changed:
                logger = BarLogger(id)
                if 'newId' in locals():
                    os.remove(path)
                    id = newId
                    path = os.path.join('videos', id)
                if audio:
                    audio.write_audiofile(path, logger=logger)
                else:
                    clip.write_videofile(path, logger=logger)
                send_email(email, path)
                os.remove(path)
                return render_template('success.html', error=error)

        return render_template('video.html', id=id, length=int(clip.duration), error=error)
    else:
        abort(404)

@app.route('/progress', methods=['GET'])
def progress():
    id = request.args.get('id')
    percentage = percentages.get(id)
    if percentage:
        return str(percentage)
    else:
        abort(404)

if __name__ == '__main__':
    if not os.path.isdir('videos'):
        os.mkdir('videos')
    app.run()
