import requests
import logging
import os
from typing import Dict, Any, Optional, Generator

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
        """Get list of products with pagination."""
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
                        "tags": True
                    }
                }
            )
            
            if not response.get('items'):
                break
                
            for item in response['items']:
                yield item
                
            if len(response['items']) < 1000:
                break
                
    def get_stock_info(self) -> Generator[Dict[Any, Any], None, None]:
        """Get stock information for all products."""
        for item in self.get_product_list():
            yield {
                "offer_id": item.get("offer_id"),
                "product_id": item.get("product_id"),
                "name": item.get("name"),
                "available": item.get("quantity", 0),
                "reserved": item.get("reserved", 0)
            }