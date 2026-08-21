from main import app

print("--- REGISTERED ROUTES ---")
for route in app.routes:
    # Handle both APIRoute and Mount objects
    methods = getattr(route, "methods", ["MOUNT"])
    print(f"{list(methods)} {route.path}")
print("--------------------------")
