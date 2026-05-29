# Deployment Guide — vidyutlabs.co.in

## Landing Page (Static)

### Option 1: GitHub Pages (Free)
```bash
# Push landing/ to gh-pages branch
cd parakram
git subtree push --prefix landing origin gh-pages
```
Then in GitHub Settings → Pages → Custom domain: `vidyutlabs.co.in`

### Option 2: Vercel (Free)
```bash
npm i -g vercel
cd landing
vercel --prod
```
Set custom domain: `vidyutlabs.co.in` in Vercel Dashboard.

### Option 3: Cloudflare Pages (Free)
1. Connect GitHub repo
2. Build command: (none — static HTML)
3. Output directory: `landing`
4. Custom domain: `vidyutlabs.co.in`

---

## Domain DNS Setup (vidyutlabs.co.in)

Add these DNS records at your registrar:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | 76.76.21.21 | Auto |
| CNAME | www | cname.vercel-dns.com | Auto |
| CNAME | api | your-backend-server.com | Auto |

---

## Backend (API Server)

### Option 1: Railway (Free tier)
```bash
# Deploy backend
cd parakram/backend
railway init
railway up
```

### Option 2: Render (Free tier)
1. New Web Service → Connect GitHub repo
2. Root directory: `backend`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Option 3: Self-hosted (VPS)
```bash
# On your server
git clone https://github.com/varshinicb1/parakram.git
cd parakram/backend
pip install -r requirements.txt
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## Docker Deployment

```bash
# Build & run
docker build -t parakram .
docker run -d -p 8000:8000 --env-file .env parakram

# With Docker Compose
docker-compose up -d
```

---

## Environment Variables (.env)

```env
OPENROUTER_API_KEY=sk-or-v1-...
SARVAM_API_KEY=...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
JWT_SECRET=your-jwt-secret-key
DATABASE_URL=sqlite:///./storage/users.db
```

---

## SSL / HTTPS

All platforms above (Vercel, Cloudflare, Railway, Render) provide free SSL certificates automatically.

For self-hosted, use Let's Encrypt:
```bash
certbot --nginx -d vidyutlabs.co.in -d www.vidyutlabs.co.in -d api.vidyutlabs.co.in
```
