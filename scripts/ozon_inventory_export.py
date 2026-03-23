import sys
import os
import json
import logging
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = "/opt/ouroboros"  # Use absolute path for container environment
sys.path.insert(0, repo_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Export inventory data from Ozon Seller API to a JSON file.
    """
    try:
        from ouroboros.ozon_api import OzonSellerAPI
        from ouroboros.api.ozon_secrets import SELLER_CLIENT_ID, SELLER_API_KEY
        
        # Initialize API client
        client = OzonSellerAPI(SELLER_CLIENT_ID, SELLER_API_KEY)
        
        # Create data directory if it doesn't exist
        data_dir = os.path.join(repo_dir, "data", "ozon")
        os.makedirs(data_dir, exist_ok=True)
        
        # File path for the output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(data_dir, f"stock_dump_{timestamp}.json")
        
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Repository directory: {repo_dir}")
        logger.info(f"Data directory: {data_dir}")
        logger.info(f"Output file path: {output_file}")
        
        logger.info("Fetching inventory data from Ozon API...")
        
        # Collect all stock information
        stock_data = []
        for item in client.get_stock_info():
            stock_data.append(item)
            
        logger.info(f"Retrieved {len(stock_data)} inventory items")
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stock_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Inventory data saved to {output_file}")
        
        # Also save a stable symlink
        stable_file = os.path.join(data_dir, "stock_dump.json")
        if os.path.exists(stable_file):
            os.remove(stable_file)
        os.symlink(output_file, stable_file)
        
        logger.info(f"Stable symlink created at {stable_file}")
        
        # Print summary
        logger.info("Summary of inventory data:")
        logger.info(f"Total SKUs: {len(stock_data)}")
        
        # Find items with available stock
        active_stock = [item for item in stock_data if item.get('available', 0) > 0]
        logger.info(f"SKUs with available stock: {len(active_stock)}")
        
        # Calculate total inventory
        total_available = sum(item.get('available', 0) for item in stock_data)
        logger.info(f"Total available inventory: {total_available} units")
        
        # Display first few items for verification
        logger.info("First 5 inventory items:")
        for i, item in enumerate(stock_data[:5]):
            logger.info(f"  {i+1}. {item.get('name', 'Unknown')}: {item.get('available', 0)} available")
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to export inventory data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()