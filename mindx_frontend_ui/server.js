const express = require('express');
const path = require('path');
const app = express();
const port = process.env.FRONTEND_PORT || 3000;

// Disable caching for development
app.use(express.static(__dirname, {
  setHeaders: (res, filePath) => {
    if (filePath.endsWith('.js') || filePath.endsWith('.css') || filePath.endsWith('.html')) {
      res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
      res.setHeader('Pragma', 'no-cache');
      res.setHeader('Expires', '0');
    }
  }
}));

// Route /login to login.html
app.get('/login', (req, res) => {
  res.sendFile(path.resolve(__dirname, 'login.html'));
});

// Route /app to app.html (protected - client-side auth check)
app.get('/app', (req, res) => {
  res.sendFile(path.resolve(__dirname, 'app.html'));
});

// Route root to login page
app.get('/', (req, res) => {
  res.redirect('/login');
});

// Fallback for SPA: serve app.html for authenticated routes, login.html for others
app.get('*', (req, res) => {
  // Check if request accepts HTML
  if (req.accepts('html')) {
    // For API-like requests, return 404
    if (req.path.startsWith('/api/') || req.path.includes('.')) {
      res.status(404).send('Not found');
      return;
    }
    // Default to login page for unknown routes
    res.redirect('/login');
  } else {
    res.status(404).send('Not found');
  }
});

app.listen(port, '0.0.0.0', () => {
  console.log(`MindX Frontend running on http://localhost:${port}`);
  console.log(`Login page: http://localhost:${port}/login`);
  console.log(`Main app: http://localhost:${port}/app`);
});
