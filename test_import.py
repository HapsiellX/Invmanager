import sys
import os

# Add the app directory to the path
sys.path.insert(0, 'app')

print("Python path:", sys.path[:3])
print("Current directory:", os.getcwd())

try:
    # Try to import just the module
    import core.database as db_module
    print("✅ Successfully imported core.database")
    
    # Check what's available
    available_attrs = [attr for attr in dir(db_module) if not attr.startswith('_')]
    print("Available attributes:", available_attrs)
    
    # Check specifically for our function
    if hasattr(db_module, 'get_db_connection'):
        print("✅ get_db_connection is available")
        func = getattr(db_module, 'get_db_connection')
        print("Function type:", type(func))
    else:
        print("❌ get_db_connection not found")
        
except ImportError as e:
    print(f"❌ Import failed: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")
