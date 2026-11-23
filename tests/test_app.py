import pytest

from ACEest_Fitness import app


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_index_lists_programs_without_selecting_one(client):
    response = client.get("/")

    assert response.status_code == 200
    for name in ("Fat Loss (FL)", "Muscle Gain (MG)", "Beginner (BG)"):
        assert name in response.text
    assert "Select a profile to view workout" in response.text
    assert "Select a profile to view diet" in response.text


@pytest.mark.parametrize(
    ("program", "workout", "diet"),
    [
        ("fat-loss", "5x5 Back Squat + AMRAP", "Target: 2,000 kcal"),
        ("muscle-gain", "Barbell Rows 4x10", "Target: 3,200 kcal"),
        ("beginner", "Circuit Training: Air Squats", "Protein: 120g/day"),
    ],
)
def test_selected_program_displays_its_workout_and_diet(client, program, workout, diet):
    response = client.get("/", query_string={"program": program})

    assert response.status_code == 200
    assert workout in response.text
    assert diet in response.text
    assert "Select a profile to view workout" not in response.text
    assert f'value="{program}" selected' in response.text


def test_unknown_program_returns_not_found(client):
    response = client.get("/", query_string={"program": "unknown"})
    assert response.status_code == 404


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}
