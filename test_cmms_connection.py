"""
Test Grashjs CMMS API Connection
This script tests the connection to the CMMS and retrieves assets
"""

import sys
from integrations.grashjs_client import GrashjsClient

def test_connection():
    """Test basic CMMS connection"""
    print("🔌 Testing Grashjs CMMS Connection...")
    print("=" * 60)

    # Initialize client
    cmms = GrashjsClient("http://localhost:8081")
    print("✅ Client initialized: http://localhost:8081")

    # Get credentials
    print("\n📝 Please enter your CMMS credentials:")
    email = input("Email: ").strip()
    password = input("Password: ").strip()

    try:
        # Login
        print("\n🔐 Logging in...")
        token = cmms.login(email, password)
        print(f"✅ Login successful!")
        print(f"   Token: {token[:30]}...")

        # Get current user
        print("\n👤 Getting user info...")
        user = cmms.get_current_user()
        print(f"✅ Logged in as: {user.get('firstName')} {user.get('lastName')}")
        print(f"   Email: {user.get('email')}")
        print(f"   Company: {user.get('company', {}).get('name', 'N/A')}")
        print(f"   Role: {user.get('role', {}).get('name', 'N/A')}")

        # Get all assets
        print("\n📦 Retrieving assets...")
        result = cmms.get_assets(size=20)
        assets = result.get('content', [])
        total = result.get('totalElements', 0)

        print(f"✅ Found {total} total assets")
        print(f"   Showing {len(assets)} assets:")
        print("-" * 60)

        if assets:
            for i, asset in enumerate(assets, 1):
                print(f"\n{i}. {asset.get('name', 'Unnamed')}")
                print(f"   ID: {asset.get('id')}")
                print(f"   Description: {asset.get('description', 'N/A')}")
                print(f"   Serial Number: {asset.get('serialNumber', 'N/A')}")
                print(f"   Model: {asset.get('model', 'N/A')}")
                print(f"   Manufacturer: {asset.get('manufacturer', 'N/A')}")
                print(f"   Status: {asset.get('status', 'N/A')}")

                # Get location info if available
                location = asset.get('location')
                if location:
                    print(f"   Location: {location.get('name', 'N/A')}")

                # Get category if available
                category = asset.get('category')
                if category:
                    print(f"   Category: {category.get('name', 'N/A')}")
        else:
            print("\n⚠️  No assets found in the system")
            print("   Create an asset in the web UI first!")

        # Test creating a new asset via API
        print("\n" + "=" * 60)
        create_test = input("\n🔧 Would you like to create a test asset via API? (y/n): ").strip().lower()

        if create_test == 'y':
            print("\n📝 Creating test asset...")
            test_asset = cmms.create_asset(
                name="Test Asset from Python",
                description="Created via API test script",
                serialNumber="TEST-001",
                model="API-TEST-MODEL",
                manufacturer="API Test Co."
            )
            print(f"✅ Test asset created!")
            print(f"   ID: {test_asset.get('id')}")
            print(f"   Name: {test_asset.get('name')}")

        # Test creating a work order
        if assets and create_test == 'y':
            print("\n" + "=" * 60)
            wo_test = input("\n🔧 Would you like to create a test work order? (y/n): ").strip().lower()

            if wo_test == 'y':
                # Use the first asset
                first_asset = assets[0]
                print(f"\n📝 Creating work order for: {first_asset.get('name')}")

                wo = cmms.create_work_order(
                    title="Test Work Order from Python",
                    description="Created via API test script",
                    asset_id=first_asset.get('id'),
                    priority="MEDIUM"
                )
                print(f"✅ Work order created!")
                print(f"   ID: #{wo.get('id')}")
                print(f"   Title: {wo.get('title')}")
                print(f"   Status: {wo.get('status')}")
                print(f"   Priority: {wo.get('priority')}")

        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("🎉 Your CMMS API connection is working perfectly!")
        print("\nNext step: Run the Telegram bot with:")
        print("   python test_telegram_bot.py")

        return True

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure CMMS is running: docker-compose ps")
        print("2. Check if you can access: http://localhost:8081")
        print("3. Verify your credentials are correct")
        return False

if __name__ == "__main__":
    test_connection()
