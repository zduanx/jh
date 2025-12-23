#!/usr/bin/env python3
"""
Test script for authentication endpoints.

This script tests:
1. Health check endpoint
2. Google OAuth token validation (requires valid Google token)
3. JWT token generation
4. Protected endpoint access with JWT

Run: python3 -m pytest auth/__tests__/test_auth.py -v
"""

import requests
import json
from datetime import datetime, timedelta
from jose import jwt
from config.settings import settings

BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_result(test_name, success, details=""):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"   {details}")
    print()


def test_health_check():
    """Test the health check endpoint"""
    print_section("TEST 1: Health Check")

    try:
        response = requests.get(f"{BASE_URL}/health")

        if response.status_code == 200:
            data = response.json()
            print_result(
                "Health endpoint",
                True,
                f"Status: {data.get('status')}, Timestamp: {data.get('timestamp')}"
            )
            return True
        else:
            print_result(
                "Health endpoint",
                False,
                f"Status code: {response.status_code}"
            )
            return False
    except Exception as e:
        print_result("Health endpoint", False, f"Error: {str(e)}")
        return False


def test_google_auth_invalid_token():
    """Test Google OAuth with invalid token (should fail)"""
    print_section("TEST 2: Google OAuth - Invalid Token")

    try:
        payload = {"token": "invalid_google_token"}
        response = requests.post(
            f"{BASE_URL}/auth/google",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        # This should fail with 401
        if response.status_code == 401:
            print_result(
                "Invalid token rejection",
                True,
                f"Correctly rejected invalid token: {response.json().get('detail')}"
            )
            return True
        else:
            print_result(
                "Invalid token rejection",
                False,
                f"Expected 401, got {response.status_code}"
            )
            return False
    except Exception as e:
        print_result("Invalid token rejection", False, f"Error: {str(e)}")
        return False


def create_mock_jwt():
    """Create a mock JWT for testing (simulating what Google OAuth would return)"""
    print_section("TEST 3: Mock JWT Creation")

    try:
        # Create a JWT with user data
        user_data = {
            "sub": "test@example.com",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
            "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        }

        token = jwt.encode(
            user_data,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        print_result(
            "Mock JWT creation",
            True,
            f"Created JWT for {user_data['email']}"
        )

        print(f"Mock JWT Token (first 50 chars): {token[:50]}...")
        return token
    except Exception as e:
        print_result("Mock JWT creation", False, f"Error: {str(e)}")
        return None


def test_protected_endpoint_no_auth():
    """Test protected endpoint without authentication"""
    print_section("TEST 4: Protected Endpoint - No Auth")

    try:
        response = requests.get(f"{BASE_URL}/api/user")

        # Should fail with 403 (Forbidden)
        if response.status_code == 403:
            print_result(
                "No auth rejection",
                True,
                "Correctly rejected request without authentication"
            )
            return True
        else:
            print_result(
                "No auth rejection",
                False,
                f"Expected 403, got {response.status_code}"
            )
            return False
    except Exception as e:
        print_result("No auth rejection", False, f"Error: {str(e)}")
        return False


def test_protected_endpoint_with_jwt(jwt_token):
    """Test protected endpoint with valid JWT"""
    print_section("TEST 5: Protected Endpoint - With Valid JWT")

    if not jwt_token:
        print_result("Protected endpoint access", False, "No JWT token provided")
        return False

    try:
        headers = {"Authorization": f"Bearer {jwt_token}"}
        response = requests.get(f"{BASE_URL}/api/user", headers=headers)

        if response.status_code == 200:
            data = response.json()
            print_result(
                "Protected endpoint access",
                True,
                f"User: {data.get('name')} ({data.get('email')})"
            )
            print(f"   Full response: {json.dumps(data, indent=2)}")
            return True
        else:
            print_result(
                "Protected endpoint access",
                False,
                f"Status code: {response.status_code}, Response: {response.text}"
            )
            return False
    except Exception as e:
        print_result("Protected endpoint access", False, f"Error: {str(e)}")
        return False


def test_protected_endpoint_expired_jwt():
    """Test protected endpoint with expired JWT"""
    print_section("TEST 6: Protected Endpoint - Expired JWT")

    try:
        # Create an expired JWT
        user_data = {
            "sub": "test@example.com",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
            "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        }

        expired_token = jwt.encode(
            user_data,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = requests.get(f"{BASE_URL}/api/user", headers=headers)

        # Should fail with 401
        if response.status_code == 401:
            print_result(
                "Expired token rejection",
                True,
                f"Correctly rejected expired token: {response.json().get('detail')}"
            )
            return True
        else:
            print_result(
                "Expired token rejection",
                False,
                f"Expected 401, got {response.status_code}"
            )
            return False
    except Exception as e:
        print_result("Expired token rejection", False, f"Error: {str(e)}")
        return False


def test_api_docs():
    """Test that API documentation is accessible"""
    print_section("TEST 7: API Documentation")

    try:
        response = requests.get(f"{BASE_URL}/docs")

        if response.status_code == 200 and "swagger" in response.text.lower():
            print_result(
                "API docs accessible",
                True,
                f"Swagger UI available at {BASE_URL}/docs"
            )
            return True
        else:
            print_result(
                "API docs accessible",
                False,
                f"Status code: {response.status_code}"
            )
            return False
    except Exception as e:
        print_result("API docs accessible", False, f"Error: {str(e)}")
        return False


def print_summary(results):
    """Print test summary"""
    print_section("TEST SUMMARY")

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"\nSuccess Rate: {(passed/total)*100:.1f}%")

    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the output above.")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  AUTHENTICATION ENDPOINT TEST SUITE")
    print(f"  Backend URL: {BASE_URL}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    results = []

    # Run tests
    results.append(test_health_check())
    results.append(test_google_auth_invalid_token())

    # Create mock JWT and test protected endpoints
    mock_jwt = create_mock_jwt()
    results.append(mock_jwt is not None)

    results.append(test_protected_endpoint_no_auth())
    results.append(test_protected_endpoint_with_jwt(mock_jwt))
    results.append(test_protected_endpoint_expired_jwt())
    results.append(test_api_docs())

    # Print summary
    print_summary(results)

    print("\n" + "="*60)
    print("  NOTE: To test actual Google OAuth:")
    print("  1. Get a real Google ID token from the frontend")
    print("  2. POST it to /auth/google")
    print("  3. Use the returned JWT to access /api/user")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Test suite error: {str(e)}")
