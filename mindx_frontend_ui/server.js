const express = require('express');
const path = require('path');
const app = express();
const port = process.env.FRONTEND_PORT || 3000;

// Disable caching for development
app.use(express.static(__dirname, {
  setHeaders: (res, path) => {
    if (path.endsWith('.js') || path.endsWith('.css') || path.endsWith('.html')) {
      res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
      res.setHeader('Pragma', 'no-cache');
      res.setHeader('Expires', '0');
    }
  }
}));

app.get('*', (req, res) => {
  res.sendFile(path.resolve(__dirname, 'index.html'));
});

app.listen(port, '0.0.0.0', () => {
  console.log(`MindX Frontend running on http://localhost:${port}`);
});
