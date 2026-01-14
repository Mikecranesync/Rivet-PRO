"""
Grashjs CMMS REST API Client for Rivet-PRO
Provides easy integration with the Grashjs CMMS backend
"""

import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


class GrashjsClient:
    """Client for interacting with Grashjs CMMS REST API"""

    def __init__(self, base_url: str = "http://localhost:8081"):
        """
        Initialize the Grashjs API client

        Args:
            base_url: Base URL of the Grashjs API (default: http://localhost:8081)
        """
        self.base_url = base_url.rstrip('/')
        self.token: Optional[str] = None
        self.session = requests.Session()

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # Authentication

    def register(self, email: str, password: str, first_name: str, last_name: str,
                 company_name: str) -> Dict[str, Any]:
        """
        Register a new user and organization

        Args:
            email: User email
            password: User password
            first_name: User first name
            last_name: User last name
            company_name: Name of the organization/company

        Returns:
            Registration response data
        """
        response = self.session.post(
            f"{self.base_url}/auth/register",
            json={
                "email": email,
                "password": password,
                "firstName": first_name,
                "lastName": last_name,
                "companyName": company_name
            }
        )
        response.raise_for_status()
        return response.json()

    def login(self, username: str, password: str) -> str:
        """
        Login and get authentication token

        Args:
            username: Username (email)
            password: Password

        Returns:
            JWT authentication token
        """
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data.get("token")
        return self.token

    def get_current_user(self) -> Dict[str, Any]:
        """Get current authenticated user info"""
        response = self.session.get(
            f"{self.base_url}/auth/me",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    # Assets (Equipment)

    def get_assets(self, search: Optional[str] = None, page: int = 0,
                   size: int = 10) -> Dict[str, Any]:
        """
        Get list of assets/equipment

        Args:
            search: Optional search query
            page: Page number (default: 0)
            size: Page size (default: 10)

        Returns:
            Paginated asset list
        """
        params = {"page": page, "size": size}
        if search:
            params["search"] = search

        response = self.session.get(
            f"{self.base_url}/assets",
            params=params,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def get_asset(self, asset_id: int) -> Dict[str, Any]:
        """Get asset by ID"""
        response = self.session.get(
            f"{self.base_url}/assets/{asset_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def create_asset(self, name: str, description: Optional[str] = None,
                     serial_number: Optional[str] = None, model: Optional[str] = None,
                     manufacturer: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Create a new asset/equipment

        Args:
            name: Asset name (required)
            description: Asset description
            serial_number: Serial number
            model: Model name/number
            manufacturer: Manufacturer name
            **kwargs: Additional asset properties

        Returns:
            Created asset data
        """
        data = {
            "name": name,
            "description": description,
            "serialNumber": serial_number,
            "model": model,
            "manufacturer": manufacturer,
            **kwargs
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        response = self.session.post(
            f"{self.base_url}/assets",
            json=data,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def update_asset(self, asset_id: int, **kwargs) -> Dict[str, Any]:
        """Update an existing asset"""
        response = self.session.patch(
            f"{self.base_url}/assets/{asset_id}",
            json=kwargs,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def delete_asset(self, asset_id: int) -> bool:
        """Delete an asset"""
        response = self.session.delete(
            f"{self.base_url}/assets/{asset_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return True

    # Work Orders

    def get_work_orders(self, status: Optional[str] = None, page: int = 0,
                        size: int = 10) -> Dict[str, Any]:
        """
        Get list of work orders

        Args:
            status: Filter by status (OPEN, IN_PROGRESS, ON_HOLD, COMPLETE)
            page: Page number
            size: Page size

        Returns:
            Paginated work order list
        """
        params = {"page": page, "size": size}
        if status:
            params["status"] = status

        response = self.session.get(
            f"{self.base_url}/work-orders",
            params=params,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def get_work_order(self, work_order_id: int) -> Dict[str, Any]:
        """Get work order by ID"""
        response = self.session.get(
            f"{self.base_url}/work-orders/{work_order_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def create_work_order(self, title: str, description: Optional[str] = None,
                          asset_id: Optional[int] = None, priority: str = "MEDIUM",
                          due_date: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Create a new work order

        Args:
            title: Work order title (required)
            description: Work order description
            asset_id: Associated asset ID
            priority: Priority level (NONE, LOW, MEDIUM, HIGH)
            due_date: Due date (ISO format: YYYY-MM-DD)
            **kwargs: Additional work order properties

        Returns:
            Created work order data
        """
        data = {
            "title": title,
            "description": description,
            "priority": priority,
            **kwargs
        }

        if asset_id:
            data["asset"] = {"id": asset_id}

        if due_date:
            data["dueDate"] = due_date

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        response = self.session.post(
            f"{self.base_url}/work-orders",
            json=data,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def update_work_order(self, work_order_id: int, **kwargs) -> Dict[str, Any]:
        """Update an existing work order"""
        response = self.session.patch(
            f"{self.base_url}/work-orders/{work_order_id}",
            json=kwargs,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def complete_work_order(self, work_order_id: int,
                           feedback: Optional[str] = None) -> Dict[str, Any]:
        """
        Mark a work order as complete

        Args:
            work_order_id: Work order ID
            feedback: Optional completion feedback

        Returns:
            Updated work order data
        """
        data = {"status": "COMPLETE"}
        if feedback:
            data["feedback"] = feedback

        return self.update_work_order(work_order_id, **data)

    def delete_work_order(self, work_order_id: int) -> bool:
        """Delete a work order"""
        response = self.session.delete(
            f"{self.base_url}/work-orders/{work_order_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return True

    # Preventive Maintenance

    def get_preventive_maintenances(self, page: int = 0, size: int = 10) -> Dict[str, Any]:
        """Get list of preventive maintenance schedules"""
        response = self.session.get(
            f"{self.base_url}/preventive-maintenances",
            params={"page": page, "size": size},
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def get_preventive_maintenance(self, pm_id: int) -> Dict[str, Any]:
        """Get preventive maintenance by ID"""
        response = self.session.get(
            f"{self.base_url}/preventive-maintenances/{pm_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def create_preventive_maintenance(self, name: str, title: str,
                                      asset_id: Optional[int] = None,
                                      frequency: int = 1,
                                      frequency_type: str = "MONTHLY",
                                      **kwargs) -> Dict[str, Any]:
        """
        Create a new preventive maintenance schedule

        Args:
            name: PM schedule name
            title: Work order title template
            asset_id: Associated asset ID
            frequency: Frequency number (e.g., 1, 2, 3)
            frequency_type: Frequency type (DAILY, WEEKLY, MONTHLY, YEARLY)
            **kwargs: Additional PM properties

        Returns:
            Created PM schedule data
        """
        data = {
            "name": name,
            "title": title,
            "schedule": {
                "frequency": frequency,
                "frequencyType": frequency_type
            },
            **kwargs
        }

        if asset_id:
            data["asset"] = {"id": asset_id}

        response = self.session.post(
            f"{self.base_url}/preventive-maintenances",
            json=data,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def update_preventive_maintenance(self, pm_id: int, **kwargs) -> Dict[str, Any]:
        """Update a preventive maintenance schedule"""
        response = self.session.patch(
            f"{self.base_url}/preventive-maintenances/{pm_id}",
            json=kwargs,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def delete_preventive_maintenance(self, pm_id: int) -> bool:
        """Delete a preventive maintenance schedule"""
        response = self.session.delete(
            f"{self.base_url}/preventive-maintenances/{pm_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return True

    # Parts & Inventory

    def get_parts(self, search: Optional[str] = None, page: int = 0,
                  size: int = 10) -> Dict[str, Any]:
        """Get list of parts"""
        params = {"page": page, "size": size}
        if search:
            params["search"] = search

        response = self.session.get(
            f"{self.base_url}/parts",
            params=params,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def get_part(self, part_id: int) -> Dict[str, Any]:
        """Get part by ID"""
        response = self.session.get(
            f"{self.base_url}/parts/{part_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def create_part(self, name: str, cost: float = 0.0, quantity: float = 0.0,
                    min_quantity: float = 0.0, description: Optional[str] = None,
                    **kwargs) -> Dict[str, Any]:
        """
        Create a new part

        Args:
            name: Part name (required)
            cost: Part cost
            quantity: Current quantity
            min_quantity: Minimum quantity (reorder threshold)
            description: Part description
            **kwargs: Additional part properties

        Returns:
            Created part data
        """
        data = {
            "name": name,
            "cost": cost,
            "quantity": quantity,
            "minQuantity": min_quantity,
            "description": description,
            **kwargs
        }
        data = {k: v for k, v in data.items() if v is not None}

        response = self.session.post(
            f"{self.base_url}/parts",
            json=data,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def update_part(self, part_id: int, **kwargs) -> Dict[str, Any]:
        """Update a part"""
        response = self.session.patch(
            f"{self.base_url}/parts/{part_id}",
            json=kwargs,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def adjust_part_quantity(self, part_id: int, quantity_change: float) -> Dict[str, Any]:
        """
        Adjust part quantity

        Args:
            part_id: Part ID
            quantity_change: Amount to add (positive) or subtract (negative)

        Returns:
            Updated part data
        """
        # First get current quantity
        part = self.get_part(part_id)
        current_qty = part.get("quantity", 0.0)
        new_qty = current_qty + quantity_change

        return self.update_part(part_id, quantity=new_qty)

    def delete_part(self, part_id: int) -> bool:
        """Delete a part"""
        response = self.session.delete(
            f"{self.base_url}/parts/{part_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return True

    # Locations

    def get_locations(self, page: int = 0, size: int = 10) -> Dict[str, Any]:
        """Get list of locations"""
        response = self.session.get(
            f"{self.base_url}/locations",
            params={"page": page, "size": size},
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def create_location(self, name: str, address: Optional[str] = None,
                        **kwargs) -> Dict[str, Any]:
        """Create a new location"""
        data = {"name": name, "address": address, **kwargs}
        data = {k: v for k, v in data.items() if v is not None}

        response = self.session.post(
            f"{self.base_url}/locations",
            json=data,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()


# Example usage
if __name__ == "__main__":
    # Initialize client
    client = GrashjsClient("http://localhost:8081")

    try:
        # Register (first time only)
        # client.register(
        #     email="admin@rivetpro.com",
        #     password="SecurePassword123",
        #     first_name="Rivet",
        #     last_name="Admin",
        #     company_name="Rivet Pro CMMS"
        #)

        # Login
        token = client.login("admin@rivetpro.com", "SecurePassword123")
        print(f"Logged in successfully. Token: {token[:20]}...")

        # Get current user
        user = client.get_current_user()
        print(f"Current user: {user.get('email')}")

        # Create an asset
        asset = client.create_asset(
            name="Motor #101",
            description="Primary conveyor motor",
            serial_number="MTR-2024-001",
            model="XYZ-500",
            manufacturer="ACME Motors"
        )
        print(f"Created asset: {asset.get('name')} (ID: {asset.get('id')})")

        # Create a work order
        wo = client.create_work_order(
            title="Replace motor bearings",
            description="Annual bearing replacement for Motor #101",
            asset_id=asset.get('id'),
            priority="HIGH",
            due_date="2026-01-15"
        )
        print(f"Created work order: {wo.get('title')} (ID: {wo.get('id')})")

        # Create a part
        part = client.create_part(
            name="Motor Bearing 6205",
            description="Standard ball bearing for motors",
            cost=25.50,
            quantity=10,
            min_quantity=5
        )
        print(f"Created part: {part.get('name')} (ID: {part.get('id')})")

        # Create PM schedule
        pm = client.create_preventive_maintenance(
            name="Monthly Motor Inspection",
            title="Inspect Motor #101",
            asset_id=asset.get('id'),
            frequency=1,
            frequency_type="MONTHLY"
        )
        print(f"Created PM schedule: {pm.get('name')} (ID: {pm.get('id')})")

        # Search assets
        assets = client.get_assets(search="motor")
        print(f"Found {len(assets.get('content', []))} assets matching 'motor'")

        # Complete work order
        completed_wo = client.complete_work_order(
            wo.get('id'),
            feedback="Bearings replaced successfully"
        )
        print(f"Completed work order: {completed_wo.get('status')}")

    except requests.exceptions.HTTPError as e:
        print(f"API Error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"Error: {str(e)}")
