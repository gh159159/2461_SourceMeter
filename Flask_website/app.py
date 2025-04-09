from flask import Flask
from static.routes import register_blueprints

app = Flask(__name__)

register_blueprints(app)

if __name__ == "__main__":
    app.run(debug=True)