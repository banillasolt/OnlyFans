import os
import json
from itertools import product
import multiprocessing
from multiprocessing import current_process, Pool
from multiprocessing.dummy import Pool as ThreadPool
import requests
from bs4 import BeautifulSoup
from urllib.request import urlretrieve
from datetime import datetime
import logging
import inspect

# Open settings.json and fill in mandatory information for the script to work
json_data = json.load(open('settings.json'))
j_directory = json_data['directory']+"/Users/"
app_token = json_data['app-token']
sess = json_data['sess']
user_agent = json_data['user-agent']
format_path = json_data['file_name_format']

auth_cookie = {
    'domain': '.onlyfans.com',
    'expires': None,
    'name': 'sess',
    'path': '/',
    'value': sess,
    'version': 0
}

session = requests.Session()
session.cookies.set(**auth_cookie)
session.headers = {
    'User-Agent': user_agent, 'Referer': 'https://onlyfans.com/'}
logging.basicConfig(filename='errors.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')


def link_check():
    link = 'https://onlyfans.com/api2/v2/subscriptions/subscribes?limit=1&offset=0&query=' + username + \
           '&app-token=' + app_token
    r = session.get(link)
    y = json.loads(r.text)
    temp_user_id2 = dict()
    if not y:
        temp_user_id2[0] = False
        temp_user_id2[1] = "No users found"
        return temp_user_id2
    if "error" in y:
        temp_user_id2[0] = False
        temp_user_id2[1] = y["error"]["message"]
        return temp_user_id2
    y = y[0]["user"]

    subbed = y["subscribedBy"]
    if not subbed:
        temp_user_id2[0] = False
        temp_user_id2[1] = "You're not subscribed to the user"
        return temp_user_id2
    else:
        temp_user_id2[0] = True
        temp_user_id2[1] = str(y["id"])
        return temp_user_id2


def scrape_choice():
    print('Scrape: a = Everything | b = Images | c = Videos')
    print('Optional Arguments: -l = Only scrape links -()- Example: "a -l"')
    input_choice = input().strip()
    image_api = "https://onlyfans.com/api2/v2/users/"+user_id+"/posts/photos?limit=100&offset=0&order=publish_date_" \
                                                              "desc&app-token="+app_token+""
    video_api = "https://onlyfans.com/api2/v2/users/"+user_id+"/posts/videos?limit=100&offset=0&order=publish_date_" \
                                                              "desc&app-token="+app_token+""
    # ARGUMENTS
    only_links = False
    if "-l" in input_choice:
        only_links = True
        input_choice = input_choice.replace(" -l", "")

    if input_choice == "a":
        location = "Images"
        media_scraper(image_api, location, j_directory, only_links)
        print("Photos Finished")
        location = "Videos"
        media_scraper(video_api, location, j_directory, only_links)
        print("Videos Finished")
        return
    if input_choice == "b":
        location = "Images"
        media_scraper(image_api, location, j_directory, only_links)
        print("Photos Finished")
        return
    if input_choice == "c":
        location = "Videos"
        media_scraper(video_api, location, j_directory, only_links)
        print("Videos Finished")
        return


def reformat(directory2, file_name2, ext, date):
    path = format_path.replace("{username}", username)
    path = path.replace("{date}", date)
    path = path.replace("{file_name}", file_name2)
    path = path.replace("{ext}", ext)
    directory2 += path
    return directory2


def media_scraper(link, location, directory, only_links):
    logger = logging.getLogger(inspect.stack()[0][3])
    next_page = True
    next_offset = 0
    media_set = dict([])
    media_count = 0
    while next_page:
        offset = next_offset
        r = session.get(link)
        y = json.loads(r.text)
        if not y:
            break
        for media_api in y:
            try:
                for media in media_api["media"]:
                    if "source" in media:
                        file = media["source"]["source"]
                        if "ca2.convert" in file:
                            file = media["preview"]
                        media_set[media_count] = {}
                        media_set[media_count]["link"] = file
                        dt = datetime.fromisoformat(media_api["postedAt"]).replace(tzinfo=None).strftime('%d-%m-%Y')
                        media_set[media_count]["text"] = media_api["text"]
                        media_set[media_count]["postedAt"] = dt
                        media_count += 1
            except Exception as e:
                logger.error(e)
                logger.error(y)
                exit()
        next_offset = offset + 100
        link = link.replace("offset="+str(offset), "offset="+str(next_offset))
    # path = reformat(media_set)
    if "/Users/" == directory:
        directory = os.path.dirname(os.path.realpath(__file__))+"/Users/"+username+"/"+location+"/"
    else:
        directory = directory+username+"/"+location+"/"

    print("DIRECTORY - " + directory)
    if not os.path.exists(directory):
        os.makedirs(directory)

    with open(directory+'links.json', 'w') as outfile:
        json.dump(media_set, outfile)
    if not only_links:
        max_threads = multiprocessing.cpu_count()
        pool = ThreadPool(max_threads)
        pool.starmap(download_media, product(media_set.items(), [directory]))


def download_media(media, directory):
    link = media[1]["link"]
    file_name = link.rsplit('/', 1)[-1]
    file_name, ext = os.path.splitext(file_name)
    ext = ext.replace(".", "")
    directory = reformat(directory, file_name, ext, media[1]["postedAt"])
    urlretrieve(link, directory)
    print(link)
    return


while True:
    print('Input a username or profile link')
    input_link = input().strip()
    username = input_link.rsplit('/', 1)[-1]

    user_id = link_check()
    if not user_id[0]:
        print(user_id[1])
        print("First time? Did you forget to edit your settings.json file?")
        continue
    user_id = user_id[1]
    scrape_choice()
    print('Everything Finished')
