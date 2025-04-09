from flask import render_template, Blueprint

view_route = Blueprint("view_route",__name__)

@view_route.route("/")
def index():
    return render_template("index.html")