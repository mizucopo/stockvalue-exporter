from flask import jsonify
from base_view import BaseView


class HealthView(BaseView):
    def get(self):
        return jsonify(
            {
                "name": self.main_app.name,
                "version": self.main_app.version,
                "description": self.main_app.description,
                "status": "running",
                "message": f"{self.main_app.name} v{self.main_app.version} is running!",
            }
        )
