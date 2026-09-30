"""Route registration and auth/contract checks for Regulatory Change Center."""


def test_regulatory_change_routes_registered():
    from app.main import app

    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/api/regulatory/change/recent" in paths
    assert "/api/regulatory/change/project/{project_id}" in paths
    assert "/api/regulatory/change/{document_id}" in paths
