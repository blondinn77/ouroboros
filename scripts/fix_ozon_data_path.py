import os
import sys

# Adjust the path to make it work in the container environment
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.join(current_dir, "../")

# Try to use the repo directory we're in
if not os.path.exists(repo_dir):
    # Fallback to a known path
    repo_dir = "/opt/ouroboros"

data_dir = os.path.join(repo_dir, "data", "ozon")
os.makedirs(data_dir, exist_ok=True)

print(f"Current directory: {os.getcwd()}")
print(f"Repository directory: {repo_dir}")
print(f"Data directory: {data_dir}")
print(f"Data directory exists: {os.path.exists(data_dir)}")

# Check write permissions
try:
    test_file = os.path.join(data_dir, "test_write.txt")
    with open(test_file, 'w') as f:
        f.write("test")
    print(f"Successfully wrote test file to {test_file}")
    os.remove(test_file)
except Exception as e:
    print(f"Failed to write to data directory: {e}")