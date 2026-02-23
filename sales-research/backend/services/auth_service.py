from dotenv import load_dotenv
import os
from supabase import create_client, Client
# Load .env from root project directory if not already loaded
# This is a bit tricky, let's try standard load_dotenv first
load_dotenv()

class AuthService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.database_url = os.getenv("DATABASE_URL")
        
        # Robust URL resolution: if url is a pooler or doesn't start with https, try to fix it
        if self.url and ("pooler.supabase.com" in self.url or not self.url.startswith("http")):
             if self.database_url and "postgres." in self.database_url:
                try:
                    # Extract project ref from postgres.[REF]:[PASS]@[HOST]
                    part1 = self.database_url.split("postgres.")[1]
                    project_ref = part1.split(":")[0]
                    self.url = f"https://{project_ref}.supabase.co"
                except:
                    pass
        
        self.client: Client = None
        if self.url and self.anon_key:
            try:
                self.client = create_client(self.url, self.anon_key)
            except Exception as e:
                print(f"Failed to create Supabase client: {e}")
            
    def sign_in(self, email, password):
        try:
            return self.client.auth.sign_in_with_password({"email": email, "password": password})
        except Exception as e:
            print(f"Sign in failed: {e}")
            return None

    def get_user(self, token):
        try:
            return self.client.auth.get_user(token)
        except Exception as e:
            return None
            
auth_service = AuthService()
