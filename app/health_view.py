from flask import jsonify
from base_view import BaseView


class HealthView(BaseView):
    def get(self):
        return jsonify(
            {
                "name": self.app.name,
                "version": self.app.version,
                "description": self.app.description,
                "status": "running",
                "message": f"{self.app.name} v{self.app.version} is running!",
            }
        )
