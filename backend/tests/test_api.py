from fastapi.testclient import TestClient

from prereqpath.api import app

client = TestClient(app)


def test_programs_lists_every_discovered_program_with_plannability():
    r = client.get("/api/programs").json()
    assert r["counts"]["discovered"] == 202
    math = next(p for p in r["programs"] if p["id"] == "mathematics-major-ba")
    assert math["plannable"] and math["verification"] == "verified"
    bio = next(p for p in r["programs"] if p["id"] == "biology-major-bs")
    assert not bio["plannable"]


def test_program_detail_keeps_sources():
    r = client.get("/api/programs/mathematics-major-ba").json()
    req = r["program"]["requirements"][0]
    assert req["source"]["url"].startswith("https://catalog.unc.edu/")
    assert req["source"]["catalog_year"] == "2026-2027"
    assert req["verification"]["status"] == "verified"


def test_placements_offered():
    r = client.get("/api/programs/mathematics-major-ba/placements").json()
    assert {"PLACEMENT:MATH 231", "PLACEMENT:MATH 232"} <= {p["token"] for p in r["placements"]}


def test_course_search_and_detail():
    r = client.get("/api/courses/search", params={"q": "math 23"}).json()
    assert r["results"][0]["code"].startswith("MATH 23")
    d = client.get("/api/courses/MATH 521").json()
    assert "MATH 381" in d["prerequisites_text"] and d["source"]["url"].endswith("/courses/math/")
    assert client.get("/api/courses/ZZZZ 999").status_code == 404


def test_plan_endpoint_round_trip():
    body = {"programs": ["mathematics-major-ba"], "entry_term": "Fall 2026", "first_term": "Spring 2027",
            "graduation_term": "Spring 2030", "completed": [{"code": "MATH 231", "grade": "A"}]}
    r = client.post("/api/plan", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "feasible" and data["graduation_certified"] is False
    assert data["plans"][0]["terms"][0]["term"] == "Spring 2027"


def test_plan_endpoint_validation_errors():
    assert client.post("/api/plan", json={"programs": ["biology-major-bs"]}).status_code == 422
    assert client.post("/api/plan", json={"programs": []}).status_code == 422
    assert client.post("/api/plan", json={"programs": ["mathematics-major-ba"],
                                          "completed": [{"code": "MATH 231", "grade": "Z"}]}).status_code == 422
    # clients cannot claim certification
    body = {"programs": ["mathematics-major-ba"], "graduation_certified": True,
            "completed": [{"code": "MATH 231", "grade": "A"}]}
    assert client.post("/api/plan", json=body).json()["graduation_certified"] is False
