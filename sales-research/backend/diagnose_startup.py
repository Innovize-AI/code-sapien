import time
import sys
import os

# Set environment to dev for measurement consistency
os.environ["ENVIRONMENT"] = "dev"

def check_startup():
    print("--- ⏱️ Glial Backend Comprehensive Startup Diagnostic ---")
    
    start_time = time.time()
    
    # Track which modules are already loaded (should be minimal)
    initial_modules = set(sys.modules.keys())
    
    try:
        from main import app
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Fast API initialized in: {duration:.2f} seconds")
        
        # Check for "leak" candidates
        leaks = []
        heavy_packages = [
            'langchain', 
            'langchain_openai', 
            'langchain_community', 
            'langgraph', 
            'pinecone',
            'openai',
            'agents.linkedin_agent'
        ]
        
        for pkg in heavy_packages:
            if pkg in sys.modules:
                leaks.append(pkg)
        
        if leaks:
            print("⚠️ Warning: Some modules were loaded prematurely:")
            for leak in leaks:
                print(f"   - {leak}")
        else:
            print("✨ Pure Startup: No heavy modules loaded at top-level!")

        # Predict Cloud Run time (usually ~2s overhead for infra + migrations)
        print(f"\n📈 Predicted Cloud Run Cold Start: ~{duration + 2.0:.2f}s")
        
    except Exception as e:
        print(f"❌ Startup Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_startup()
