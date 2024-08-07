import http.server
import socketserver
import json
import os
from urllib.parse import parse_qs
from datetime import datetime
import re
import sqlite3
import subprocess
import sys

PORT = 8000

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = 'templates/index.html'
        elif self.path == '/book':
            self.path = 'templates/book.html'
        elif self.path == '/view_bookings':
            self.path = 'templates/view_bookings.html'
        elif self.path == '/bookings':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            bookings = self.load_bookings()
            self.wfile.write(json.dumps(bookings).encode())
            return
        elif self.path == '/confirmation':
            self.path = 'templates/confirmation.html'
        elif self.path == '/favicon.ico':
            self.path = 'favicon.ico'
        else:
            self.send_error(404, "File not found")
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/book':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode()
            data = parse_qs(post_data)
            name = data.get('name', [''])[0]
            date = data.get('date', [''])[0]
            time = data.get('time', [''])[0]

            # Validate data
            if not name or not date or not time:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'All fields are required.')
                return

            name_pattern = re.compile(r'^[A-Za-z\s]+$')
            if not name_pattern.match(name):
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'Name should contain only alphabetic characters and spaces.')
                return

            try:
                selected_datetime = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
                if selected_datetime < datetime.now():
                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'The selected date and time must be in the future.')
                    return
            except ValueError:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'Invalid date or time format.')
                return

            self.save_booking(name, date, time)

            self.send_response(302)
            self.send_header('Location', '/confirmation')
            self.end_headers()

    def load_bookings(self):
        conn = sqlite3.connect('bookings.db')
        cur = conn.cursor()
        cur.execute('SELECT name, date, time FROM bookings')
        bookings = cur.fetchall()
        conn.close()
        return [{'name': row[0], 'date': row[1], 'time': row[2]} for row in bookings]

    def save_booking(self, name, date, time):
        conn = sqlite3.connect('bookings.db')
        cur = conn.cursor()
        cur.execute('INSERT INTO bookings (name, date, time) VALUES (?, ?, ?)', (name, date, time))
        conn.commit()
        conn.close()

Handler = MyHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Serving at {url}")

    # Open URL in the default web browser using subprocess
    try:
        if sys.platform == "win32":
            subprocess.run(["start", url], check=True, shell=True)
        elif sys.platform == "darwin":
            subprocess.run(["open", url], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", url], check=True)
    except Exception as e:
        print(f"Failed to open URL: {e}")

    httpd.serve_forever()

