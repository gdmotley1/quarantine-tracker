const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const PORT = 3000;
const DIR = __dirname;

// MIME types for static files
const MIME = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
  // Serve static files only — data is handled by Supabase
  const safePath = path.normalize(req.url.split('?')[0]).replace(/^(\.\.[\/\\])+/, '');
  let filePath = path.join(DIR, safePath === '/' || safePath === '\\' ? 'index.html' : safePath);
  const ext = path.extname(filePath).toLowerCase();

  try {
    if (!filePath.startsWith(DIR)) {
      res.writeHead(403);
      res.end('Forbidden');
      return;
    }
    const content = fs.readFileSync(filePath);
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    res.end(content);
  } catch {
    res.writeHead(404);
    res.end('Not found');
  }
});

server.listen(PORT, '0.0.0.0', () => {
  const nets = os.networkInterfaces();
  let localIP = 'localhost';
  for (const name of Object.keys(nets)) {
    for (const net of nets[name]) {
      if (net.family === 'IPv4' && !net.internal) {
        localIP = net.address;
        break;
      }
    }
  }

  console.log('');
  console.log('  ======================================');
  console.log('  FOUTS BROS INC - Quarantine Tracker');
  console.log('  ======================================');
  console.log('');
  console.log('  Local dev server running (static files only)');
  console.log('  Data is stored in Supabase');
  console.log('');
  console.log('  http://localhost:' + PORT);
  console.log('  http://' + localIP + ':' + PORT);
  console.log('');
  console.log('  Press Ctrl+C to stop.');
  console.log('');
});
