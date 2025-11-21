# FX Confluence Dashboard

This is a **React + Vite dashboard** displaying forex, indices, and commodities confluence trends across multiple timeframes. It connects to a Flask backend providing confluence data.

---

## Features

* Real-time confluence trends (Weekly, Daily, H4, H1)
* Bullish / Bearish / Strong trends visualization
* Breakdown percentages and summary bars
* Responsive, polished UI

---

## Frontend Setup

### Install dependencies

```bash
npm install
```

### Development mode

```bash
npm run dev
```

* Opens the dashboard at `http://localhost:5173` (default Vite port)

### Preview production build

```bash
npm run preview
```

* Serves the `dist` folder at port 5000 by default

### Build for production

```bash
npm run build
```

* Outputs static files to `dist`

---

## Environment Variables

* **VITE_API_URL**: Backend API endpoint (optional, defaults to hardcoded backend URL)

Example `.env` file:

```
VITE_API_URL=https://backend-qxff.onrender.com
```

---

## Deployment

* Build frontend: `npm run build`
* Serve with static server (Render, Netlify, or Vercel)
* Backend should be accessible at `VITE_API_URL`

---

## Project Structure

```
frontend/
├─ src/
│  ├─ main.jsx         # React entry point
│  ├─ App.jsx          # Main dashboard component
│  ├─ api.js           # API helper for fetching confluence data
│  └─ style.css        # Styles
├─ index.html          # HTML template
├─ package.json        # Frontend dependencies and scripts
└─ vite.config.js      # Vite configuration
```

---

## Learn More

* [Vite Documentation](https://vitejs.dev/)
* [React Documentation](https://reactjs.org/)
* [Flask Documentation](https://flask.palletsprojects.com/)
