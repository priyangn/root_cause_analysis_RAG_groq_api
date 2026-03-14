import requests
import sys
import time
import json
from datetime import datetime
from pathlib import Path
import tempfile

class RCAAPITester:
    def __init__(self, base_url="https://root-cause-ai-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.uploaded_files = []
        self.current_analysis = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)
        
        if files and 'Content-Type' in test_headers:
            del test_headers['Content-Type']  # Let requests set this for multipart

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, headers=test_headers)
                else:
                    response = requests.post(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed")
                try:
                    response_data = response.json() if response.content else {}
                except:
                    response_data = {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text[:200]}")
                response_data = {}

            return success, response_data

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_register(self):
        """Test user registration"""
        timestamp = datetime.now().strftime('%H%M%S')
        user_data = {
            "email": f"test_user_{timestamp}@example.com",
            "password": "TestPass123!",
            "full_name": "Test Engineer"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=user_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response.get('user', {})
            print(f"   Token received: {self.token[:20]}...")
            return True
        return False

    def test_login(self):
        """Test user login with registered credentials"""
        if not self.user_data:
            print("❌ No user data available for login test")
            return False
            
        login_data = {
            "email": self.user_data['email'],
            "password": "TestPass123!"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   New token received: {self.token[:20]}...")
            return True
        return False

    def test_auth_me(self):
        """Test authenticated user info retrieval"""
        success, response = self.run_test(
            "Get User Info",
            "GET",
            "auth/me",
            200
        )
        return success and 'email' in response

    def test_file_upload(self):
        """Test file upload functionality"""
        # Create a test CSV file
        test_content = """timestamp,temperature,vibration,load,pressure
2024-01-01 10:00:00,85.2,0.5,1000,15.2
2024-01-01 10:01:00,87.1,0.7,1050,15.8
2024-01-01 10:02:00,92.3,1.2,1100,16.5
2024-01-01 10:03:00,95.1,2.1,1150,17.2
2024-01-01 10:04:00,98.5,3.5,1200,18.1"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(test_content)
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                files = {'file': ('test_data.csv', f, 'text/csv')}
                success, response = self.run_test(
                    "File Upload",
                    "POST",
                    "upload",
                    200,
                    files=files
                )
            
            if success and 'id' in response:
                self.uploaded_files.append(response['id'])
                print(f"   File ID: {response['id']}")
                return True
            return False
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_list_uploads(self):
        """Test listing uploaded files"""
        success, response = self.run_test(
            "List Uploads",
            "GET",
            "upload",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} uploaded files")
            return True
        return False

    def test_start_analysis(self):
        """Test starting analysis pipeline"""
        if not self.uploaded_files:
            print("❌ No uploaded files available for analysis")
            return False
        
        analysis_data = {
            "file_ids": self.uploaded_files[:1]  # Use first uploaded file
        }
        
        success, response = self.run_test(
            "Start Analysis",
            "POST",
            "analysis/start",
            200,
            data=analysis_data
        )
        
        if success and 'id' in response:
            self.current_analysis = response['id']
            print(f"   Analysis ID: {self.current_analysis}")
            return True
        return False

    def test_get_analysis(self):
        """Test retrieving analysis results"""
        if not self.current_analysis:
            print("❌ No current analysis available")
            return False
        
        success, response = self.run_test(
            "Get Analysis",
            "GET",
            f"analysis/{self.current_analysis}",
            200
        )
        
        if success and 'status' in response:
            print(f"   Status: {response['status']}")
            print(f"   Progress: {response.get('progress', 0)}%")
            return True
        return False

    def test_list_analyses(self):
        """Test listing all analyses"""
        success, response = self.run_test(
            "List Analyses",
            "GET",
            "analysis",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} analyses")
            return True
        return False

    def test_chat_functionality(self):
        """Test chat functionality"""
        chat_data = {
            "message": "What are the main indicators of machine failure?",
            "analysis_id": self.current_analysis
        }
        
        success, response = self.run_test(
            "Chat Message",
            "POST",
            "chat",
            200,
            data=chat_data
        )
        
        if success and 'response' in response:
            print(f"   Response length: {len(response['response'])} chars")
            return True
        return False

    def test_download_report(self):
        """Test report download functionality"""
        if not self.current_analysis:
            print("❌ No current analysis available for report download")
            return False
        
        # Note: This endpoint returns a file, not JSON
        url = f"{self.api_url}/reports/{self.current_analysis}/download"
        headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
        
        self.tests_run += 1
        print(f"\n🔍 Testing Report Download...")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed")
                print(f"   Report size: {len(response.content)} bytes")
                return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_delete_file(self):
        """Test file deletion"""
        if not self.uploaded_files:
            print("❌ No uploaded files to delete")
            return False
        
        file_id = self.uploaded_files[0]
        success, response = self.run_test(
            "Delete File",
            "DELETE",
            f"upload/{file_id}",
            200
        )
        
        if success:
            self.uploaded_files.remove(file_id)
            return True
        return False

    def wait_for_analysis_completion(self, timeout=60):
        """Wait for analysis to complete or timeout"""
        if not self.current_analysis:
            return False
        
        print(f"\n⏳ Waiting for analysis completion (timeout: {timeout}s)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            success, response = self.run_test(
                "Analysis Status Check",
                "GET",
                f"analysis/{self.current_analysis}",
                200
            )
            
            if success:
                status = response.get('status')
                progress = response.get('progress', 0)
                print(f"   Progress: {progress}% - Status: {status}")
                
                if status in ['completed', 'failed']:
                    return status == 'completed'
            
            time.sleep(5)
        
        print("❌ Analysis timeout")
        return False

def main():
    tester = RCAAPITester()
    
    print("🚀 Starting RCA Platform API Tests")
    print(f"Base URL: {tester.base_url}")
    print("=" * 50)
    
    # Test sequence
    tests = [
        ("Registration", tester.test_register),
        ("Login", tester.test_login), 
        ("Auth Me", tester.test_auth_me),
        ("File Upload", tester.test_file_upload),
        ("List Uploads", tester.test_list_uploads),
        ("Start Analysis", tester.test_start_analysis),
        ("Get Analysis", tester.test_get_analysis),
        ("List Analyses", tester.test_list_analyses),
        ("Chat Functionality", tester.test_chat_functionality),
        ("Download Report", tester.test_download_report),
        ("Delete File", tester.test_delete_file),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        try:
            if not test_func():
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            failed_tests.append(test_name)
    
    # Wait for analysis completion if one was started
    if tester.current_analysis:
        analysis_completed = tester.wait_for_analysis_completion()
        if analysis_completed:
            print("\n✅ Analysis completed successfully")
            # Retest analysis results after completion
            tester.test_get_analysis()
        else:
            failed_tests.append("Analysis Completion")
    
    print("\n" + "=" * 50)
    print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    if failed_tests:
        print(f"❌ Failed tests: {', '.join(failed_tests)}")
        return 1
    else:
        print("✅ All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())