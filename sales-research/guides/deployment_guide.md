# Production Deployment Guide

This guide covers how to deploy the `sales-research` system (Backend + Frontend + Database) to a production environment (e.g., VPS, AWS EC2, DigitalOcean Droplet).

## Prerequisites

1.  **A Server (VPS)**: Ubuntu 22.04 LTS recommended.
2.  **Domain Name**: Pointed to your server IP.
3.  **Third-Party Accounts**: OpenAI, Tavily, RapidAPI, Apollo, Supabase, Pinecone keys ready (See `environment_variables.md`).

---

## Step 1: Clone & Configure via Git

SSH into your server and clone the repository:

```bash
git clone https://github.com/Innovize-AI/code-sapien.git
cd code-sapien/sales-research
```

Create your production environment file:

```bash
cp backend/.env.example backend/.env
nano backend/.env
# Paste all your production keys here
```

---

## Step 2: Use Docker Compose (Recommended)

Docker simplifies valid deployment by containerizing both the Python backend and Next.js frontend.

### Create `docker-compose.yml`

Copy this configuration to your project root:

```yaml
version: "3.8"

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: sales_user
      POSTGRES_PASSWORD: secure_password
      POSTGRES_DB: sales_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql+asyncpg://sales_user:secure_password@db:5432/sales_db
    depends_on:
      - db
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend

volumes:
  postgres_data:
```

### Run It

```bash
docker-compose up -d --build
```

---

## Step 3: Nginx Reverse Proxy (SSL)

To serve your app securely on `https://yourdomain.com`, set up Nginx.

1.  **Install Nginx**: `sudo apt install nginx`
2.  **Configure Site**: `sudo nano /etc/nginx/sites-available/sales-research`

    ```nginx
    server {
        server_name yourdomain.com;

        location / {
            proxy_pass http://localhost:3000; # Frontend
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }

        location /api {
            proxy_pass http://localhost:8000; # Backend
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }
    }
    ```

3.  **Enable & Restart**:
    ```bash
    sudo ln -s /etc/nginx/sites-available/sales-research /etc/nginx/sites-enabled/
    sudo systemctl restart nginx
    ```
4.  **Get SSL (Certbot)**:
    ```bash
    sudo apt install certbot python3-certbot-nginx
    sudo certbot --nginx -d yourdomain.com
    ```

---

## Step 4: Automate Background Tasks

Ensure your background scheduler runs smoothly. If using `supervisord` or `systemd` (instead of Docker for backend):

1.  Create a service file: `/etc/systemd/system/sales-backend.service`
2.  Command: `/path/to/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000`
3.  Enable: `sudo systemctl enable sales-backend`

---

## Maintenance

- **Database Migrations**: `docker-compose exec backend alembic upgrade head`
- **Logs**: `docker-compose logs -f backend`
