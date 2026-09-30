def test_compliance_routes_registered():
    from app.main import app

    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/api/compliance/{project_id}" in paths
    assert "/api/compliance/items/{item_id}/complete" in paths
    assert "/api/compliance/{project_id}/renewals" in paths
    assert "/api/compliance/renewals/{renewal_id}" in paths
