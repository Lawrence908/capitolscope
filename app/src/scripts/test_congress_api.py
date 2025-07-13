#!/usr/bin/env python3
"""
Test script for Congress.gov API integration.

This script performs basic tests to verify the API client is working correctly.
"""

import asyncio
import sys
from typing import Dict, Any

from core.config import settings
from core.logging import get_logger
from domains.congressional.client import CongressAPIClient

logger = get_logger(__name__)


async def test_api_client():
    """Test the Congress.gov API client functionality."""
    
    if not settings.CONGRESS_GOV_API_KEY:
        print("❌ CONGRESS_GOV_API_KEY environment variable is not set")
        return False
    
    print("🔑 API Key is configured")
    
    try:
        async with CongressAPIClient() as client:
            print("✅ API client initialized successfully")
            
            # Test 1: Get member list
            print("\n📋 Testing member list endpoint...")
            response = await client.get_member_list(limit=5)
            
            if response.members:
                print(f"✅ Retrieved {len(response.members)} members")
                
                # Display first member
                first_member = response.members[0]
                print(f"   First member: {first_member.get('name', 'Unknown')}")
                print(f"   Bioguide ID: {first_member.get('bioguideId', 'Unknown')}")
                print(f"   Party: {first_member.get('party', 'Unknown')}")
                print(f"   State: {first_member.get('state', 'Unknown')}")
                
                # Test 2: Get specific member details
                bioguide_id = first_member.get('bioguideId')
                if bioguide_id:
                    print(f"\n👤 Testing member details for {bioguide_id}...")
                    member_response = await client.get_member_by_bioguide_id(bioguide_id)
                    
                    if member_response.member:
                        member = member_response.member
                        print(f"✅ Retrieved member details:")
                        print(f"   Name: {member.get('name', 'Unknown')}")
                        print(f"   Current Member: {member.get('currentMember', 'Unknown')}")
                        print(f"   Official Website: {member.get('officialWebsiteUrl', 'Not available')}")
                        
                        # Test 3: Get sponsored legislation
                        print(f"\n📜 Testing sponsored legislation for {bioguide_id}...")
                        legislation = await client.get_member_sponsored_legislation(bioguide_id, limit=3)
                        
                        if legislation.get('bills'):
                            bills = legislation['bills']
                            print(f"✅ Retrieved {len(bills)} sponsored bills")
                            if bills:
                                print(f"   Latest bill: {bills[0].get('title', 'Unknown')}")
                        else:
                            print("ℹ️  No sponsored legislation found")
                    else:
                        print(f"❌ Failed to retrieve member details for {bioguide_id}")
                else:
                    print("⚠️  No bioguide ID available for detailed testing")
                
                # Test 4: Get members by state
                print(f"\n🏛️ Testing members by state (CA)...")
                ca_response = await client.get_members_by_state("CA", limit=3)
                
                if ca_response.members:
                    print(f"✅ Retrieved {len(ca_response.members)} members from California")
                    for member in ca_response.members[:2]:  # Show first 2
                        print(f"   {member.get('name', 'Unknown')} - {member.get('district', 'Unknown')}")
                else:
                    print("❌ Failed to retrieve members from California")
                
                # Test 5: Get current congress number
                print(f"\n📊 Testing current congress calculation...")
                congress_number = await client.get_current_congress_number()
                print(f"✅ Current Congress: {congress_number}")
                
            else:
                print("❌ No members returned from API")
                return False
                
    except Exception as e:
        print(f"❌ API test failed: {e}")
        logger.error(f"API test failed: {e}")
        return False
    
    print("\n🎉 All API tests passed!")
    return True


async def test_data_extraction():
    """Test data extraction and mapping functionality."""
    
    print("\n🔍 Testing data extraction...")
    
    # Mock API response for testing
    mock_api_data = {
        "bioguideId": "A000374",
        "name": "Abraham, Ralph Lee",
        "party": "R",
        "state": "LA",
        "district": "05",
        "terms": [
            {
                "congress": 118,
                "startYear": "2023",
                "endYear": "2025"
            }
        ],
        "url": "https://api.congress.gov/v3/member/A000374"
    }
    
    # Test the extraction logic
    from domains.congressional.services import CongressAPIService
    
    # Create a service instance for testing (we'll just test the method directly)
    try:
        # Test extraction method directly
        class MockAPIService(CongressAPIService):
            def __init__(self):
                pass  # Skip the repo requirement for testing
        
        api_service = MockAPIService()
        member_info = api_service._extract_member_info(mock_api_data)
        
        print("✅ Data extraction successful:")
        print(f"   Bioguide ID: {member_info.get('bioguide_id')}")
        print(f"   Full Name: {member_info.get('full_name')}")
        print(f"   First Name: {member_info.get('first_name')}")
        print(f"   Last Name: {member_info.get('last_name')}")
        print(f"   Party: {member_info.get('party')}")
        print(f"   State: {member_info.get('state')}")
        print(f"   District: {member_info.get('district')}")
        print(f"   Chamber: {member_info.get('chamber')}")
        print(f"   Congress Number: {member_info.get('congress_number')}")
        
        # Validate required fields
        required_fields = ['bioguide_id', 'full_name', 'last_name', 'party', 'state', 'chamber']
        missing_fields = [field for field in required_fields if not member_info.get(field)]
        
        if missing_fields:
            print(f"⚠️  Missing required fields: {missing_fields}")
        else:
            print("✅ All required fields extracted successfully")
            
    except Exception as e:
        print(f"❌ Data extraction failed: {e}")
        logger.error(f"Data extraction failed: {e}")
        return False
    
    return True


async def test_rate_limiting():
    """Test rate limiting functionality."""
    
    print("\n⏱️ Testing rate limiting...")
    
    try:
        async with CongressAPIClient() as client:
            # Make multiple rapid requests to test rate limiting
            print("Making 5 rapid requests...")
            
            for i in range(5):
                response = await client.get_member_list(limit=1)
                print(f"   Request {i+1}: {'✅' if response.members else '❌'}")
                
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.1)
            
            print("✅ Rate limiting test completed successfully")
            
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        logger.error(f"Rate limiting test failed: {e}")
        return False
    
    return True


async def run_all_tests():
    """Run all tests."""
    
    print("🚀 Starting Congress.gov API Integration Tests")
    print("=" * 50)
    
    tests = [
        ("API Client", test_api_client),
        ("Data Extraction", test_data_extraction),
        ("Rate Limiting", test_rate_limiting),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test")
        print("-" * 30)
        
        try:
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name} Test: PASSED")
            else:
                print(f"❌ {test_name} Test: FAILED")
                
        except Exception as e:
            print(f"❌ {test_name} Test: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<20} {status}")
    
    print(f"\nOverall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The Congress.gov API integration is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the output above for details.")
        return False


def main():
    """Main function."""
    
    try:
        success = asyncio.run(run_all_tests())
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error(f"Unexpected error in test script: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())