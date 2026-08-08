#!/usr/bin/env python3
import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer


class QRHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = """<!DOCTYPE html>
<html>
<head>
    <title>WhatsApp QR Code - Live</title>
    <style>
        body {
            background: #0a0a0a;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            padding: 20px;
            text-align: center;
        }
        h1 { color: #00ff00; }
        #qr-container {
            background: white;
            padding: 40px;
            display: inline-block;
            margin: 20px auto;
            border-radius: 10px;
        }
        #qr {
            font-size: 4px;
            line-height: 4px;
            letter-spacing: 0;
            white-space: pre;
            color: black;
            font-weight: bold;
        }
        #status { margin: 20px; font-size: 18px; }
        .connected { color: #00ff00; }
        .waiting { color: #ffaa00; }
    </style>
</head>
<body>
    <h1>📱 WhatsApp QR Code - LIVE</h1>
    <div id='status' class='waiting'>Waiting for QR code...</div>
    <div id='qr-container'>
        <pre id='qr'>Loading...</pre>
    </div>
    <p>Scan this QR code with WhatsApp on your phone</p>
    <p>Settings → Linked Devices → Link a Device</p>
    <script>
        async function updateQR() {
            try {
                const response = await fetch('/qr-data');
                const data = await response.json();

                if (data.connected) {
                    document.getElementById('status').innerHTML = '✅ CONNECTED!';
                    document.getElementById('status').className = 'connected';
                    document.getElementById('qr').textContent = 'WhatsApp is connected!';
                } else if (data.qr) {
                    document.getElementById('status').innerHTML = '⏳ Scan QR Code Below';
                    document.getElementById('status').className = 'waiting';
                    document.getElementById('qr').textContent = data.qr;
                } else {
                    document.getElementById('qr').textContent = 'Generating new QR code...';
                }
            } catch (e) {
                console.error('Error:', e);
            }
        }

        setInterval(updateQR, 2000);
        updateQR();
    </script>
</body>
</html>"""
            self.wfile.write(html.encode())

        elif self.path == "/qr-data":
            result = subprocess.run(
                ["docker", "logs", "bijou-whatsapp-bridge", "--tail", "50"],
                capture_output=True,
                text=True,
            )
            logs = result.stdout + result.stderr

            try:
                health = subprocess.run(
                    ["curl", "-s", "http://localhost:8080/health"],
                    capture_output=True,
                    text=True,
                )
                health_data = json.loads(health.stdout)
                connected = health_data.get("connected", False)
            except:
                connected = False

            qr_text = ""
            if not connected:
                lines = logs.split("\n")
                qr_lines = []
                in_qr = False
                for line in lines:
                    if "Scan this QR" in line:
                        qr_lines = []
                        in_qr = True
                    elif in_qr and ("█" in line or "▄" in line or "▀" in line):
                        qr_lines.append(line)
                    elif in_qr and qr_lines and line.strip() == "":
                        break

                qr_text = "\n".join(qr_lines[-35:]) if qr_lines else ""

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            response = {"connected": connected, "qr": qr_text}
            self.wfile.write(json.dumps(response).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8888), QRHandler)
    print("QR Server running on port 8888")
    server.serve_forever()
