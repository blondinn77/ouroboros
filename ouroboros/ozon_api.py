import requests
import logging
import os
from typing import Dict, Any, Optional, List, Generator

class OzonSellerAPI:
    """
    Client for Ozon Seller API (admin read only)
    Documentation: https://docs.ozon.ru/api/seller/
    """
    
    BASE_URL = "https://api-seller.ozon.ru"
    
    def __init__(
        self, 
        client_id: str, 
        api_key: str,
        base_url: str = BASE_URL
    ):
        self.client_id = client_id
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        })
        self.log = logging.getLogger("OzonSellerAPI")
        
    def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[Any, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[Any, Any]:
        """Make a request to the API."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                json=data,
                params=params,
                timeout=30
            )
            
            if response.status_code == 429:
                self.log.warning("Rate limit exceeded. Retrying after 60 seconds.")
                time.sleep(60)
                return self._request(method, endpoint, data, params)
                
            response.raise_for_status()
            result = response.json()
            
            if 'result' in result:
                return result['result']
            return result
            
        except requests.exceptions.RequestException as e:
            self.log.error(f"API request failed: {e}")
            raise
            
    def get_product_info(self, product_id: int) -> Dict[Any, Any]:
        """Get product info by ID."""
        return self._request(
            'POST', 
            '/v2/product/info', 
            data={"product_id": product_id}
        )
        
    def get_product_list(self, **kwargs) -> Generator[Dict[Any, Any], None, None]:
        """Get list of products with pagination and detailed information."""
        last_id = 0
        while True:
            response = self._request(
                'POST',
                '/v3/product/list',
                data={
                    "offset": 0,
                    "limit": 1000,
                    "filter": {
                        "visibility": "ALL",
                        "with_discount": "ALL"
                    },
                    "with": {
                        "category": True,
                        "images": True,
                        "attributes": True,
                        "price": True,
                        "analytics_data": True,
                        "tags": True,
                        "documents": True,
                        "characteristics": True,
                        "premium_benefits": True
                    }
                }
            )
            
            if not response.get('items'):
                break
                
            for item in response['items']:
                yield item
                
            if len(response['items']) < 1000:
                break
                
    def get_stocks_info(self, product_ids: Optional[List[int]] = None) -> List[Dict[Any, Any]]:
        """
        Get actual stock counts for products using the recommended /v4/product/info/stocks endpoint.
        This method should be used instead of `get_stock_info` for accurate data.
        https://developers.ozon.ru/api/seller/methods/v4.product.info.stocks
        
        Args:
            product_ids: List of product IDs to query. If None, gets IDs from get_product_list.

        Returns:
            List of dicts with 'product_id', 'offer_id', 'present', 'reserved'.
        """
        if product_ids is None:
            # Fetch all product IDs
            product_ids = [item["product_id"] for item in self.get_product_list()]

        result = self._request(
            'POST',
            '/v4/product/info/stocks',
            data={
                "product_id": product_ids,
                "warehouse_type": "ALL"  # Include All warehouses: cross-docking, FBS, FBO, RFBS
            }
        )

        stocks = []
        for item in result.get('stocks', []):
            # The response contains multiple entries per offer_id (for different warehouses), 
            # so we need to aggregate
            offer_id = item['offer_id']
            
            # Sum `present` and `reserved` across all warehouse entries
            total_present = sum([w['present'] for w in item['stocks']])
            total_reserved = sum([w['reserved'] for w in item['stocks']])
            
            stocks.append({
                "offer_id": offer_id,
                "product_id": item['product_id'],
                "present": total_present,
                "reserved": total_reserved
            })
        
        return stocks
        
    def get_stock_info(self) -> Generator[Dict[Any, Any], None, None]:
        """Deprecated. Use `get_stocks_info()` for accurate data."""
        
        # DEPRECATED: This method uses /v3/product/list which does not provide accurate stock data.
        # It is kept for backward compatibility but should not be used.
        for item in self.get_product_list():
            yield {
                "offer_id": item.get("offer_id"),
                "product_id": item.get("product_id"),
                "name": item.get("name"),
                "available": item.get("quantity", 0),
                "reserved": item.get("reserved", 0)
            }