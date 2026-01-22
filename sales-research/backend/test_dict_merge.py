from workflow.state import reduce_dict

def test_merge():
    print("Testing reduce_dict...")
    
    # Initial state (simulating empty start)
    current_val = {}
    
    # Step 1: Profile Fetcher Update
    update1 = {"name": "John Doe", "headline": "CEO"}
    current_val = reduce_dict(current_val, update1)
    print(f"After Header Fetch: {current_val}")
    
    # Step 2: Posts Fetcher Update
    update2 = {"recent_posts": ["Post 1", "Post 2"]}
    current_val = reduce_dict(current_val, update2)
    print(f"After Posts Fetch: {current_val}")
    
    # Step 3: Test List Input (Parallel Simulation)
    update3 = [{"Parallel Key 1": "Value 1"}, {"Parallel Key 2": "Value 2"}]
    current_val = reduce_dict(current_val, update3)
    print(f"After Parallel Fetch: {current_val}")
    
    # Assertions
    assert current_val["name"] == "John Doe"
    assert "recent_posts" in current_val
    assert len(current_val["recent_posts"]) == 2
    assert current_val["Parallel Key 1"] == "Value 1"
    assert current_val["Parallel Key 2"] == "Value 2"
    
    print("SUCCESS: Dictionary keys were merged correctly (including list input).")

if __name__ == "__main__":
    test_merge()
