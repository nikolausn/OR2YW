from OR2YW import OR2YWGenerator
from flask import Flask
from flask import json
from flask import request


app = Flask(__name__)

@app.route("/generate-image",method=["POST"])
def generate_image():
    if request.headers['Content-Type'] == 'application/json':
        operations = "JSON Message: " + json.dumps(request.json)

        operation_json = OR2YWGenerator.generate_yw_script(operations)
        image_encoded = OR2YWGenerator.generate_yw_image(operation_json)

        return "data:image/png;base64,{}".format(image_encoded)

if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0")
