"""
Client for Ozon Seller API.
See: https://docs.ozon.ru/api/seller/
"""

import requests
import json
from datetime import datetime, date
from typing import Optional, Dict, List, Any

from ouroboros.api.ozon_secrets import SELLER_CLIENT_ID, SELLER_API_KEY


class OzonSellerAPI:
    def __init__(self):
        self.client_id = SELLER_CLIENT_ID
        self.api_key = SELLER_API_KEY
        self.base_url = "https://api-seller.ozon.ru"
        self.session = requests.Session()
        self.session.headers.update({
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        })

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make an authenticated request to the Ozon API."""
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, json=data)
        response.raise_for_status()
        return response.json()

    def get_product_list(self) -> List[Dict]:
        """Get list of products. Returns raw API response."""
        data = {"filter": {"visibility": "ALL"}}
        return self._make_request("POST", "/v2/product/info", data=data)

    def get_product_info(self, product_id: int) -> Dict:
        """Get detailed info for a specific product."""
        data = {"product_id": product_id}
        return self._make_request("POST", "/v2/product/info", data=data)
    
    def get_product_info_by_sku(self, sku: int) -> Dict:
        """Get product info by SKU."""
        data = {"offer_id": str(sku)}  # Assuming SKU is used as offer_id
        return self._make_request("POST", "/v2/product/info", data=data)

    def get_finance_report(self, from_date: date, to_date: date) -> Dict:
        """Get financial report for a given date range."""
        data = {
            "date_from": from_date.isoformat(),
            "date_to": to_date.isoformat(),
            "type": "detail"
        }
        return self._make_request("POST", "/v3/finance/transaction/list", data=data)
    
    def get_warehouse_stock(self) -> List[Dict]:
        """Get current stock levels on Ozon's warehouse."""
        data = {"filter": {}}
        return self._make_request("POST", "/v1/stock", data=data)
    
    def get_financial_status(self) -> Dict:
        """Get current financial status (balance, etc.)."""
        return self._make_request("GET", "/v1/finance/balance")

    def get_order_list(self, from_date_iso: str, to_date_iso: str) -> List[Dict]:
        """Get list of orders in a date range."""
        data = {
            "dir": "ASC",
            "filter": {
                "canceled": False,
                "date_from": from_date_iso,
                "date_to": to_date_iso,
                "delivering_date": {},
                "status": ""
            },
            "limit": 1000,
            "offset": 0,
            "translit": False,
            "with": {
                "analytics_data": False,
                "financial_data": False
            }
        }
        return self._make_request("POST", "/v2/posting/fbo/list", data=data)['result']

    def get_posting_details(self, posting_number: str) -> Dict:
        """Get detailed information about a specific posting (order)."""
        data = {
            "posting_number": posting_number,
            "with": {
                "analytics_data": True,
                "financial_data": True,
                "translit": False
            }
        }
        return self._make_request("POST", "/v3/posting/fbo/detail", data=data)
    
    # Methods for Performance API would go here, using the separate credentials.
    # For now, a placeholder.
    def get_performance_stats(self):
        """Placeholder for Performance API integration."""
        return "Performance API integration not yet implemented."


def get_client() -> OzonSellerAPI:
    """Get a configured OzonSellerAPI client instance."""
    return OzonSellerAPI()