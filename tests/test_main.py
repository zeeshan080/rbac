from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

def test_create_user():
    response = client.post(
        "/users/",
        json={"email": "test@example.com", "password": "password123"},
    )
    # This will fail if the database is not clean for each test run
    # For a real application, you'd use a test database and clear it.
    if response.status_code == 400:
        assert response.json() == {"detail": "Email already registered"}
    else:
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        # Test reading the created user
        user_id = data["id"]
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"


def test_create_item_for_user():
    # First, create a user
    response = client.post(
        "/users/",
        json={"email": "itemuser@example.com", "password": "password123"},
    )
    if response.status_code == 400 and response.json()["detail"] == "Email already registered":
        # User already exists, try to get its ID
        # This is a simplistic way, ideally you'd fetch the user by email if GET /users/by_email existed
        # Or ensure a clean state for tests
        users_response = client.get("/users/")
        existing_users = users_response.json()
        user_id = None
        for u in existing_users:
            if u["email"] == "itemuser@example.com":
                user_id = u["id"]
                break
        if user_id is None:
            # If still not found, something is wrong, fail the test
            assert False, "Could not retrieve existing user ID for item test"
    else:
        assert response.status_code == 200
        user_data = response.json()
        user_id = user_data["id"]

    # Now create an item for this user
    response = client.post(
        f"/items/?user_id={user_id}", # Pass user_id as query parameter
        json={"title": "Test Item", "description": "This is a test item"},
    )
    assert response.status_code == 200
    item_data = response.json()
    assert item_data["title"] == "Test Item"
    assert item_data["description"] == "This is a test item"
    assert item_data["owner_id"] == user_id
