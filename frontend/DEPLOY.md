# Sanlam Funeral Plan - Netlify Deployment

[![Netlify Status](https://api.netlify.com/api/v1/badges/YOUR-SITE-ID/deploy-status)](https://app.netlify.com/sites/YOUR-SITE-NAME/deploys)

## Quick Deploy

### Option 1: Netlify CLI (Recommended)

1. **Install Netlify CLI:**
   ```bash
   npm install -g netlify-cli
   ```

2. **Login to Netlify:**
   ```bash
   netlify login
   ```

3. **Deploy:**
   ```bash
   cd frontend
   netlify deploy --prod
   ```

### Option 2: Drag & Drop

1. **Build the app:**
   ```bash
   cd frontend
   npm run build
   ```

2. **Go to:** https://app.netlify.com/drop
3. **Drag the `dist` folder** to the upload area

### Option 3: Git Integration (Best for updates)

1. Push your code to GitHub/GitLab
2. Connect repository in Netlify dashboard
3. Auto-deploys on every push!

## Environment Variables

If you need backend API access, add these in Netlify dashboard:
- `VITE_API_URL` - Your backend URL (if deployed separately)

## Custom Domain

In Netlify dashboard:
1. Go to Domain Settings
2. Add custom domain (e.g., `sanlam.yourdomain.com`)
3. Update DNS records as instructed

## Backend Note

⚠️ **Important:** The Python backend (`server.py`) needs separate hosting:
- Deploy to: Heroku, Railway, Render, or PythonAnywhere
- Update `vite.config.js` proxy target to production backend URL
- Or use serverless functions (Netlify Functions with Python runtime)
