import requests
import sys
import json
import io
import pandas as pd
from datetime import datetime
from pathlib import Path

class DataAnalyticsAPITester:
    def __init__(self, base_url="https://analytics-engine-19.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.dataset_id = None
        self.merged_dataset_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        headers = {'Content-Type': 'application/json'} if not files else {}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files)
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        return success

    def test_root_endpoint(self):
        """Test root API endpoint"""
        success, response = self.run_test(
            "Root Endpoint",
            "GET",
            "",
            200
        )
        return success

    def create_sample_csv(self):
        """Create a sample CSV file for testing"""
        data = {
            'date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
            'revenue': [1000, 1200, 800, 1500, 1100],
            'customers': [50, 60, 40, 75, 55],
            'category': ['A', 'B', 'A', 'C', 'B'],
            'region': ['North', 'South', 'North', 'West', 'South']
        }
        df = pd.DataFrame(data)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        return csv_buffer.getvalue().encode('utf-8')

    def test_file_upload(self):
        """Test file upload endpoint"""
        csv_content = self.create_sample_csv()
        files = {'file': ('test_data.csv', csv_content, 'text/csv')}
        
        success, response = self.run_test(
            "File Upload",
            "POST",
            "upload",
            200,
            files=files
        )
        
        if success and 'id' in response:
            self.dataset_id = response['id']
            print(f"📊 Dataset ID: {self.dataset_id}")
            print(f"📊 Rows: {response.get('row_count')}, Columns: {response.get('column_count')}")
            return True
        return False

    def test_list_datasets(self):
        """Test list datasets endpoint"""
        success, response = self.run_test(
            "List Datasets",
            "GET",
            "datasets",
            200
        )
        return success

    def test_get_dataset(self):
        """Test get dataset metadata"""
        if not self.dataset_id:
            print("❌ No dataset ID available")
            return False
            
        success, response = self.run_test(
            "Get Dataset Metadata",
            "GET",
            f"datasets/{self.dataset_id}",
            200
        )
        return success

    def test_preview_dataset(self):
        """Test dataset preview with pagination"""
        if not self.dataset_id:
            print("❌ No dataset ID available")
            return False
            
        success, response = self.run_test(
            "Dataset Preview",
            "GET",
            f"datasets/{self.dataset_id}/preview?page=1&page_size=10",
            200
        )
        
        if success:
            print(f"📊 Preview data: {len(response.get('data', []))} rows")
            print(f"📊 Total rows: {response.get('total_rows')}")
        
        return success

    def test_generate_dashboard(self):
        """Test dashboard generation"""
        if not self.dataset_id:
            print("❌ No dataset ID available")
            return False
            
        success, response = self.run_test(
            "Generate Dashboard",
            "GET",
            f"datasets/{self.dataset_id}/dashboard",
            200
        )
        
        if success:
            print(f"📊 KPIs: {len(response.get('kpis', []))}")
            print(f"📊 Charts: {len(response.get('charts', []))}")
            print(f"📊 Correlations: {len(response.get('correlations', []))}")
            print(f"📊 Anomalies: {len(response.get('anomalies', []))}")
        
        return success

    def test_ai_insights(self):
        """Test AI insights generation"""
        if not self.dataset_id:
            print("❌ No dataset ID available")
            return False
            
        success, response = self.run_test(
            "AI Insights",
            "POST",
            f"datasets/{self.dataset_id}/ai-insights",
            200,
            data={"dataset_id": self.dataset_id, "question": "What are the key trends in this data?"}
        )
        
        if success:
            print(f"🧠 Insights: {len(response.get('insights', []))}")
            print(f"🧠 Recommendations: {len(response.get('recommendations', []))}")
            print(f"🧠 Key findings: {len(response.get('key_findings', []))}")
        
        return success

    def test_filter_data(self):
        """Test data filtering"""
        if not self.dataset_id:
            print("❌ No dataset ID available")
            return False
            
        filters = [
            {"column": "revenue", "operator": "gt", "value": 1000}
        ]
        
        success, response = self.run_test(
            "Filter Data",
            "POST",
            f"datasets/{self.dataset_id}/filter",
            200,
            data=filters
        )
        
        if success:
            print(f"🔍 Filtered rows: {response.get('filtered_count')}")
        
        return success

    def test_aggregate_data(self):
        """Test data aggregation"""
        if not self.dataset_id:
            print("❌ No dataset ID available")
            return False
            
        agg_request = {
            "dataset_id": self.dataset_id,
            "group_by": ["category"],
            "aggregations": {"revenue": "sum", "customers": "mean"},
            "filters": []
        }
        
        success, response = self.run_test(
            "Aggregate Data",
            "POST",
            f"datasets/{self.dataset_id}/aggregate",
            200,
            data=agg_request
        )
        
        if success:
            print(f"📊 Aggregated rows: {response.get('row_count')}")
        
        return success

    def test_generate_report(self):
        """Test report generation"""
        if not self.dataset_id:
            print("❌ No dataset ID available")
            return False
            
        report_request = {
            "dataset_id": self.dataset_id,
            "report_type": "business",
            "sections": ["summary", "kpis", "trends", "recommendations"]
        }
        
        success, response = self.run_test(
            "Generate Report",
            "POST",
            f"datasets/{self.dataset_id}/report",
            200,
            data=report_request
        )
        
        if success:
            print(f"📄 Report title: {response.get('title')}")
            print(f"📄 KPIs: {len(response.get('kpis', []))}")
        
        return success

    def create_second_sample_csv(self):
        """Create a second sample CSV file for merge testing"""
        data = {
            'date': ['2024-01-06', '2024-01-07', '2024-01-08'],
            'revenue': [1300, 900, 1600],
            'customers': [65, 45, 80],
            'category': ['A', 'B', 'C'],
            'region': ['East', 'North', 'South']
        }
        df = pd.DataFrame(data)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        return csv_buffer.getvalue().encode('utf-8')

    def test_merge_datasets_concat(self):
        """Test dataset merge with concatenation"""
        if not self.dataset_id:
            print("❌ No dataset ID available")
            return False
        
        # Upload second dataset
        csv_content = self.create_second_sample_csv()
        files = {'file': ('test_data2.csv', csv_content, 'text/csv')}
        
        success, response = self.run_test(
            "Upload Second Dataset for Merge",
            "POST",
            "upload",
            200,
            files=files
        )
        
        if not success or 'id' not in response:
            return False
        
        dataset2_id = response['id']
        print(f"📊 Second Dataset ID: {dataset2_id}")
        
        # Test concatenation merge
        merge_request = {
            "dataset1_id": self.dataset_id,
            "dataset2_id": dataset2_id,
            "merge_type": "concat"
        }
        
        success, response = self.run_test(
            "Merge Datasets (Concat)",
            "POST",
            "datasets/merge",
            200,
            data=merge_request
        )
        
        if success:
            print(f"📊 Merged Dataset ID: {response.get('id')}")
            print(f"📊 Merged Rows: {response.get('row_count')}")
            print(f"📊 Merged Columns: {response.get('column_count')}")
            # Store merged dataset ID for cleanup
            self.merged_dataset_id = response.get('id')
        
        return success

    def test_merge_datasets_join(self):
        """Test dataset merge with join"""
        if not self.dataset_id:
            print("❌ No dataset ID available")
            return False
        
        # Create datasets with common join key
        data1 = {
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'score': [85, 92, 78]
        }
        df1 = pd.DataFrame(data1)
        csv_buffer1 = io.StringIO()
        df1.to_csv(csv_buffer1, index=False)
        csv_content1 = csv_buffer1.getvalue().encode('utf-8')
        
        data2 = {
            'id': [1, 2, 4],
            'department': ['Engineering', 'Marketing', 'Sales'],
            'salary': [75000, 65000, 55000]
        }
        df2 = pd.DataFrame(data2)
        csv_buffer2 = io.StringIO()
        df2.to_csv(csv_buffer2, index=False)
        csv_content2 = csv_buffer2.getvalue().encode('utf-8')
        
        # Upload first dataset for join
        files1 = {'file': ('employees.csv', csv_content1, 'text/csv')}
        success, response1 = self.run_test(
            "Upload First Join Dataset",
            "POST",
            "upload",
            200,
            files=files1
        )
        
        if not success:
            return False
        
        join_dataset1_id = response1['id']
        
        # Upload second dataset for join
        files2 = {'file': ('departments.csv', csv_content2, 'text/csv')}
        success, response2 = self.run_test(
            "Upload Second Join Dataset",
            "POST",
            "upload",
            200,
            files=files2
        )
        
        if not success:
            return False
        
        join_dataset2_id = response2['id']
        
        # Test left join
        merge_request = {
            "dataset1_id": join_dataset1_id,
            "dataset2_id": join_dataset2_id,
            "merge_type": "left_join",
            "join_key": "id"
        }
        
        success, response = self.run_test(
            "Merge Datasets (Left Join)",
            "POST",
            "datasets/merge",
            200,
            data=merge_request
        )
        
        if success:
            print(f"📊 Left Join Result - Rows: {response.get('row_count')}")
            print(f"📊 Left Join Result - Columns: {response.get('column_count')}")
        
        # Test inner join
        merge_request["merge_type"] = "inner_join"
        
        success2, response2 = self.run_test(
            "Merge Datasets (Inner Join)",
            "POST",
            "datasets/merge",
            200,
            data=merge_request
        )
        
        if success2:
            print(f"📊 Inner Join Result - Rows: {response2.get('row_count')}")
            print(f"📊 Inner Join Result - Columns: {response2.get('column_count')}")
        
        return success and success2

    def test_delete_dataset(self):
        """Test dataset deletion"""
        if not self.dataset_id:
            print("❌ No dataset ID available")
            return False
            
        success, response = self.run_test(
            "Delete Dataset",
            "DELETE",
            f"datasets/{self.dataset_id}",
            200
        )
        return success

def main():
    print("🚀 Starting Data Analytics API Tests")
    print("=" * 50)
    
    tester = DataAnalyticsAPITester()
    
    # Test sequence
    tests = [
        ("Health Check", tester.test_health_check),
        ("Root Endpoint", tester.test_root_endpoint),
        ("File Upload", tester.test_file_upload),
        ("List Datasets", tester.test_list_datasets),
        ("Get Dataset", tester.test_get_dataset),
        ("Preview Dataset", tester.test_preview_dataset),
        ("Generate Dashboard", tester.test_generate_dashboard),
        ("AI Insights", tester.test_ai_insights),
        ("Filter Data", tester.test_filter_data),
        ("Aggregate Data", tester.test_aggregate_data),
        ("Generate Report", tester.test_generate_report),
        ("Merge Datasets (Concat)", tester.test_merge_datasets_concat),
        ("Merge Datasets (Join)", tester.test_merge_datasets_join),
        ("Delete Dataset", tester.test_delete_dataset),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        try:
            if not test_func():
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            failed_tests.append(test_name)
    
    # Print results
    print("\n" + "=" * 50)
    print(f"📊 Tests completed: {tester.tests_passed}/{tester.tests_run}")
    print(f"✅ Success rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    if failed_tests:
        print(f"\n❌ Failed tests: {', '.join(failed_tests)}")
        return 1
    else:
        print("\n🎉 All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())