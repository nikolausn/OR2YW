from OR2YW import OR2YWGenerator
from flask import Flask


app = Flask(__name__)
or2yw = OR2YW()

@app.route("/generate-image")
def generate_image(operations):
    return