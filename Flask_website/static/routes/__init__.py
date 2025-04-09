from .view_route import view_route
from .measure_route import measure_route

blueprints = [
    (view_route,"/"),
    (measure_route,"/api/measure")
]

def register_blueprints(app):
    for blueprint,prefix in blueprints:
        app.register_blueprint(blueprint,url_prefix=prefix)