from flask import Flask, render_template
import os
from glob import glob

app = Flask(__name__)
PHOTO_FOLDER = '/home/pi/static/photos' 


@app.route('/')
def index():
    # Get list of image files sorted by most recent
    files = sorted(glob(os.path.join(PHOTO_FOLDER, '*.jpg')), key=os.path.getmtime, reverse=True)
    latest_photos = files[:15]  # Get 9 most recent
    filenames = [os.path.basename(f) for f in latest_photos]
    return render_template('index.html', filenames=filenames)
