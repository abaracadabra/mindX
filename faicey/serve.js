/**
 * Simple HTTP server for viewing the holographic face in browser
 */

import { createServer } from 'http';
import { readFileSync } from 'fs';
import { extname, join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PORT = 8080;

const mimeTypes = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
};

const server = createServer((req, res) => {
    console.log(`${req.method} ${req.url}`);

    let filePath = req.url === '/'
        ? join(__dirname, 'examples', 'holographic-face.html')
        : join(__dirname, req.url);

    const ext = extname(filePath).toLowerCase();
    const contentType = mimeTypes[ext] || 'application/octet-stream';

    try {
        const content = readFileSync(filePath);
        res.writeHead(200, {
            'Content-Type': contentType,
            'Access-Control-Allow-Origin': '*'
        });
        res.end(content, 'utf-8');
    } catch (error) {
        if (error.code === 'ENOENT') {
            res.writeHead(404);
            res.end('File not found');
        } else {
            res.writeHead(500);
            res.end('Server error: ' + error.code);
        }
    }
});

server.listen(PORT, () => {
    console.log('\n╔════════════════════════════════════════════════╗');
    console.log('║   Faicey Holographic Face Server Running      ║');
    console.log('╚════════════════════════════════════════════════╝\n');
    console.log(`  🌐 Server running at: http://localhost:${PORT}/`);
    console.log(`  📂 Serving files from: ${__dirname}`);
    console.log('\n  Press Ctrl+C to stop\n');
});
