import os
import json
import glob

def get_userdata_path():
    cache_path = os.path.join(os.getcwd(), ".storage", "cache")
    userdata_path = glob.glob(cache_path + "/user_*.json")
    return userdata_path[0]

def get_userdata():
    userdata_path = get_userdata_path()
    userdata = json.load(open(userdata_path))
    return userdata