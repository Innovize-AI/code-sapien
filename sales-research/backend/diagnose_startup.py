import time
import os
import sys

def benchmark_startup():
    print("--- ⏱️ Glial Backend Startup Diagnostic ---")
    
    # 1. Measure pure import time of FastAPI app
    start_time = time.time()
    
    try:
        from main import app
        end_time = time.time()
        import_duration = end_time - start_time
        
        print(f"✅ Fast API initialized in: {import_duration:.2f} seconds")
        
        # 2. Check for "Import Avalanches"
        # Since we use lazy loading, these should NOT be in sys.modules yet
        heavy_modules = [
            'agents.linkedin_agent',
            'agents.website_agent',
            'agents.lead_scoring_agent',
            'workflow.graph'
        ]
        
        avalanches = [m for m in heavy_modules if m in sys.modules]
        
        if not avalanches:
            print("✅ Success: No heavy agent modules were loaded during startup.")
            print("🚀 Result: Your cold start will be extremely fast.")
        else:
            print("⚠️ Warning: Some modules were loaded prematurely:")
            for m in avalanches:
                print(f"   - {m}")
        
        # 3. Predict Cloud Run Readiness
        # Container is "Ready" once FastAPI is initialized. 
        # Cloud Run adds ~2s for infrastructure setup.
        predicted_cold_start = import_duration + 2.0
        print(f"\n📈 Predicted Cloud Run Cold Start: ~{predicted_cold_start:.2f}s")
        
    except ImportError as e:
        print(f"❌ Error: Missing dependencies to run diagnostic: {e}")
        print("💡 Run this inside your virtual environment (e.g., source venv/bin/activate)")
    except Exception as e:
        print(f"❌ Unexpected error during benchmark: {e}")

if __name__ == "__main__":
    benchmark_startup()
