const express = require('express');
const path = require('path');
const app = express();
const port = process.env.FRONTEND_PORT || 3000;

app.use(express.static(__dirname));

app.get('*', (req, res) => {
  res.sendFile(path.resolve(__dirname, 'index.html'));
});

app.listen(port, '0.0.0.0', () => {
  console.log(`MindX Frontend running on http://localhost:${port}`);
});
