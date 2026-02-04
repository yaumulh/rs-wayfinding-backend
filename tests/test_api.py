"""
Backend API Tests for Hospital AR Navigation App
Tests: Locations CRUD, Admin PIN verification
"""
import pytest
import requests
import os
import uuid

# Get BASE_URL from environment (origin without /api). Prefer BACKEND_TEST_BASE_URL or REACT_APP_BACKEND_URL.
BASE_URL = os.environ.get('BACKEND_TEST_BASE_URL') or os.environ.get('REACT_APP_BACKEND_URL') or 'http://localhost:8000'
BASE_URL = BASE_URL.rstrip('/')
API_BASE = f"{BASE_URL}/api"
# Timeout for requests (seconds)
REQUEST_TIMEOUT = int(os.environ.get('BACKEND_TEST_TIMEOUT', '10'))
# Admin PIN for tests
ADMIN_PIN = os.environ.get('TEST_ADMIN_PIN', '1234')
# Mark these as integration tests
pytestmark = pytest.mark.integration

class TestHealthAndRoot:
    """Test basic API health and root endpoint"""
    
    def test_api_root(self):
        """Test API root endpoint returns welcome message"""
        response = requests.get(f"{API_BASE}/", timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Hospital AR Navigation API" in data["message"]


class TestAdminPinVerification:
    """Test admin PIN verification endpoint"""
    
    def test_verify_pin_success(self):
        """Test PIN verification with correct PIN '1234'"""
        response = requests.post(
            f"{API_BASE}/admin/verify-pin",
            json={"pin": ADMIN_PIN},
            timeout=REQUEST_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "PIN verified" in data["message"]
    
    def test_verify_pin_invalid(self):
        """Test PIN verification with wrong PIN"""
        response = requests.post(
            f"{API_BASE}/admin/verify-pin",
            json={"pin": "0000"},
            timeout=REQUEST_TIMEOUT
        )
        assert response.status_code == 401
        data = response.json()
        assert "Invalid PIN" in data.get("detail", "")
    
    def test_verify_pin_empty(self):
        """Test PIN verification with empty PIN"""
        response = requests.post(
            f"{API_BASE}/admin/verify-pin",
            json={"pin": ""},
            timeout=REQUEST_TIMEOUT
        )
        assert response.status_code == 401


class TestLocationsCRUD:
    """Test Locations CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data prefix for cleanup"""
        self.test_prefix = "TEST_"
        self.created_ids = []
        yield
        # Cleanup: Delete all test-created locations (log if deletion fails)
        for loc_id in self.created_ids:
            try:
                r = requests.delete(f"{API_BASE}/locations/{loc_id}", timeout=REQUEST_TIMEOUT)
                if r.status_code != 200:
                    print(f"Cleanup warning: deleting {loc_id} returned {r.status_code}: {r.text[:200]}")
            except Exception as e:
                print(f"Cleanup exception deleting {loc_id}: {e}")
    
    def test_get_locations_list(self):
        """Test GET /api/locations returns list"""
        response = requests.get(f"{API_BASE}/locations", timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_location(self):
        """Test POST /api/locations creates new location"""
        unique_name = f"{self.test_prefix}Radiology_{uuid.uuid4().hex[:6]}"
        payload = {
            "name": unique_name,
            "description": "Test radiology department",
            "coordinates": {"x": 10.5, "y": 0, "z": 15.2}
        }
        
        response = requests.post(
            f"{API_BASE}/locations",
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Validate response structure
        assert "id" in data
        assert data["name"] == unique_name
        assert data["description"] == "Test radiology department"
        assert data["coordinates"]["x"] == 10.5
        assert data["coordinates"]["z"] == 15.2
        
        self.created_ids.append(data["id"])
        
        # Verify persistence with GET
        get_response = requests.get(f"{API_BASE}/locations/{data['id']}", timeout=REQUEST_TIMEOUT)
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["name"] == unique_name
    
    def test_create_location_with_icon(self):
        """Test creating location with icon_url"""
        unique_name = f"{self.test_prefix}Pharmacy_{uuid.uuid4().hex[:6]}"
        payload = {
            "name": unique_name,
            "description": "Hospital pharmacy",
            "coordinates": {"x": 5.0, "y": 0, "z": 8.0},
            "icon_url": "/api/uploads/pharmacy-icon.png"
        }
        
        response = requests.post(
            f"{API_BASE}/locations",
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["icon_url"] == "/api/uploads/pharmacy-icon.png"
        
        self.created_ids.append(data["id"])
    
    def test_get_single_location(self):
        """Test GET /api/locations/{id} returns single location"""
        # First create a location
        unique_name = f"{self.test_prefix}Emergency_{uuid.uuid4().hex[:6]}"
        create_response = requests.post(
            f"{API_BASE}/locations",
            json={
                "name": unique_name,
                "coordinates": {"x": 0, "y": 0, "z": 20}
            },
            timeout=REQUEST_TIMEOUT
        )
        assert create_response.status_code == 201
        location_id = create_response.json()["id"]
        self.created_ids.append(location_id)
        
        # Get the location
        response = requests.get(f"{API_BASE}/locations/{location_id}", timeout=REQUEST_TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == location_id
        assert data["name"] == unique_name
    
    def test_get_nonexistent_location(self):
        """Test GET /api/locations/{id} returns 404 for non-existent"""
        fake_id = str(uuid.uuid4())
        response = requests.get(f"{API_BASE}/locations/{fake_id}", timeout=REQUEST_TIMEOUT)
        assert response.status_code == 404
    
    def test_update_location(self):
        """Test PUT /api/locations/{id} updates location"""
        # Create location first
        unique_name = f"{self.test_prefix}Lab_{uuid.uuid4().hex[:6]}"
        create_response = requests.post(
            f"{API_BASE}/locations",
            json={
                "name": unique_name,
                "description": "Original description",
                "coordinates": {"x": 1, "y": 0, "z": 1}
            },
            timeout=REQUEST_TIMEOUT
        )
        assert create_response.status_code == 201
        location_id = create_response.json()["id"]
        self.created_ids.append(location_id)
        
        # Update the location
        update_payload = {
            "name": f"{unique_name}_Updated",
            "description": "Updated description",
            "coordinates": {"x": 2, "y": 0, "z": 3}
        }
        
        update_response = requests.put(
            f"{API_BASE}/locations/{location_id}",
            json=update_payload,
            timeout=REQUEST_TIMEOUT
        )
        
        assert update_response.status_code == 200
        updated_data = update_response.json()
        assert updated_data["name"] == f"{unique_name}_Updated"
        assert updated_data["description"] == "Updated description"
        assert updated_data["coordinates"]["x"] == 2
        
        # Verify persistence
        get_response = requests.get(f"{API_BASE}/locations/{location_id}", timeout=REQUEST_TIMEOUT)
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["name"] == f"{unique_name}_Updated"
    
    def test_update_partial_location(self):
        """Test partial update (only some fields)"""
        # Create location
        unique_name = f"{self.test_prefix}ICU_{uuid.uuid4().hex[:6]}"
        create_response = requests.post(
            f"{API_BASE}/locations",
            json={
                "name": unique_name,
                "description": "Intensive Care Unit",
                "coordinates": {"x": 5, "y": 0, "z": 10}
            },
            timeout=REQUEST_TIMEOUT
        )
        assert create_response.status_code == 201
        location_id = create_response.json()["id"]
        self.created_ids.append(location_id)
        
        # Update only description
        update_response = requests.put(
            f"{API_BASE}/locations/{location_id}",
            json={"description": "Updated ICU description"},
            timeout=REQUEST_TIMEOUT
        )
        
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["name"] == unique_name  # Name unchanged
        assert updated["description"] == "Updated ICU description"
    
    def test_update_nonexistent_location(self):
        """Test PUT /api/locations/{id} returns 404 for non-existent"""
        fake_id = str(uuid.uuid4())
        response = requests.put(
            f"{API_BASE}/locations/{fake_id}",
            json={"name": "Test"},
            timeout=REQUEST_TIMEOUT
        )
        assert response.status_code == 404
    
    def test_delete_location(self):
        """Test DELETE /api/locations/{id} removes location"""
        # Create location
        unique_name = f"{self.test_prefix}ToDelete_{uuid.uuid4().hex[:6]}"
        create_response = requests.post(
            f"{API_BASE}/locations",
            json={
                "name": unique_name,
                "coordinates": {"x": 0, "y": 0, "z": 0}
            },
            timeout=REQUEST_TIMEOUT
        )
        assert create_response.status_code == 201
        location_id = create_response.json()["id"]
        
        # Delete the location
        delete_response = requests.delete(f"{API_BASE}/locations/{location_id}", timeout=REQUEST_TIMEOUT)
        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["success"] == True
        
        # Verify deletion
        get_response = requests.get(f"{API_BASE}/locations/{location_id}", timeout=REQUEST_TIMEOUT)
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_location(self):
        """Test DELETE /api/locations/{id} returns 404 for non-existent"""
        fake_id = str(uuid.uuid4())
        response = requests.delete(f"{API_BASE}/locations/{fake_id}", timeout=REQUEST_TIMEOUT)
        assert response.status_code == 404


class TestLocationValidation:
    """Test location input validation"""
    
    def test_create_location_missing_name(self):
        """Test creating location without name fails"""
        response = requests.post(
            f"{API_BASE}/locations",
            json={
                "coordinates": {"x": 0, "y": 0, "z": 0}
            },
            timeout=REQUEST_TIMEOUT
        )
        assert response.status_code == 422  # Validation error
    
    def test_create_location_missing_coordinates(self):
        """Test creating location without coordinates fails"""
        response = requests.post(
            f"{API_BASE}/locations",
            json={
                "name": "Test Location"
            },
            timeout=REQUEST_TIMEOUT
        )
        assert response.status_code == 422  # Validation error
