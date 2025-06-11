from flask import jsonify
from base_view import BaseView


class VersionView(BaseView):
    def get(self):
        return jsonify(
            {
                "name": self.app.name,
                "version": self.app.version,
                "description": self.app.description,
            }
        )
