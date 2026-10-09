from pathlib import Path
import re

from fastapi.testclient import TestClient

from brewflow.application import create_app
from brewflow.settings import QueueSettings


FRONTEND_DIST = Path("frontend/dist")


def test_production_frontend_is_served_by_fastapi(tmp_path):
    assert (FRONTEND_DIST / "index.html").is_file(), (
        "Build the frontend before running this integration suite"
    )

    app = create_app(
        database_uri=f"sqlite+aiosqlite:///{tmp_path / 'integration.db'}",
        frontend_dist=FRONTEND_DIST,
        queue_settings=QueueSettings(
            drinks=("Latte",),
            milks=("Whole",),
            textures=("Wet",),
            search_depth=0,
            max_batch_volume=5,
        ),
    )

    with TestClient(app) as client:
        for page in ("/api/queue", "/api/history"):
            response = client.get(page)
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/html")
            assert '<title>BrewFlow</title>' in response.text

            scripts = re.findall(r'<script[^>]+src="([^"]+)"', response.text)
            stylesheets = re.findall(r'<link[^>]+href="([^"]+)"', response.text)
            assert scripts and all(path.startswith("/assets/") for path in scripts)
            assert stylesheets and all(path.startswith("/assets/") for path in stylesheets)

            script = client.get(scripts[0])
            stylesheet = client.get(stylesheets[0])
            assert script.status_code == 200
            assert script.headers["content-type"].startswith("text/javascript")
            assert "Queue" in script.text
            assert stylesheet.status_code == 200
            assert stylesheet.headers["content-type"].startswith("text/css")
            assert "#17212b" in stylesheet.text

        assert client.get("/api/unknown").status_code == 404
        assert client.get("/assets/missing.js").status_code == 404
