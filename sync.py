#! /usr/bin/env python
#coding=utf-8

import os.path
from hashlib import md5, sha1
import shutil
import traceback
from threading import Thread, Event
import bsddb
from api import upload_dir
from monitor import monitor_black_list
from cfg import get_cfg_dir
import time

blacklist = set()
g_ind = None

def sync_folder(client, path, localpath, evt, db, local_path):
    fileinfo = client.fileinfo(path, root="kuaipan")
    print('begin sync %s -> %s, hash is %s' % (path, localpath, fileinfo['hash']))
    filesets = set()
    syncdirlist=[]
    for file in fileinfo['files']:
        if evt.isSet():
            break
        lpath = os.path.join(localpath, file['name'])
        rpath = os.path.join(path, file['name'])

        if not file['is_deleted']:
            path_key = md5(rpath).hexdigest()
            #print('rpath: %s - %s' % (rpath, type(rpath)))
            filesets.add(rpath)
            if file['type'] == 'folder':
                if not os.path.exists(lpath):
                    print('mkdir %s' % lpath)
                    os.mkdir(lpath)
                #sync_folder(rpath, lpath, evt, db)
                syncdirlist.append((client, rpath, lpath, evt, db, local_path))
            else:
                #print("%s's sha1 is %s" % (file['name'], file['sha1']))
                if os.path.exists(lpath):
                    if not db.has_key(path_key):
                        f = open(lpath, 'r')
                        data = f.read()
                        db[path_key] = sha1(data).hexdigest()
                        f.close()
                    assert db.has_key(path_key)
                    if db[path_key] == file['sha1']:
                        #print("%s is exist, and sha1 is the smae" % lpath)
                        continue
                    else:
                        print("%s is exist and sha1 is not same, download and overwrite" % lpath)
                try:
                    print('begin download %s -> %s' % (rpath, lpath))
                    monitor_black_list.add(lpath)
                    data = client.download(rpath[1:])
                    f = open(lpath, 'wb')
                    f.write(data)
                    f.close()
                    db[path_key] = file['sha1']
                except:
                    print(traceback.format_exc())
        else:
            print('------%s is deleted from kuaipan------' % rpath)
            if file['type'] == 'folder':
                if os.path.exists(lpath):
                    print('delete folder %s' % lpath)
                    monitor_black_list.add(lpath)
                    shutil.rmtree(lpath)
            else:
                if os.path.exists(lpath):
                    print('delete file %s' % lpath)
                    monitor_black_list.add(lpath)
                    os.remove(lpath)
    
    for afile in os.listdir(localpath):
        filepath = os.path.join(localpath, afile)
        if os.path.isfile(filepath):
            kpath = filepath[len(local_path):]
            kpath = kpath.decode('utf8') if isinstance(kpath, str) else kpath
            if kpath not in filesets:
                #print('%s (%s) is not in set([%s])' % (kpath, type(kpath), ','.join(list(filesets))))
                if kpath not in blacklist:
                    print('upload local file %s -> %s' % (filepath, kpath))
                    client.upload(kpath, filepath)

        if os.path.isdir(filepath):
            inpath = filepath[len(local_path):]
            inpath = inpath.decode('utf8') if isinstance(inpath, str) else inpath
            if inpath not in filesets:
                #print('%s (%s) is not in set([%s])' % (inpath, type(inpath), ','.join(list(filesets))))
                if inpath not in blacklist:
                    print('upload local dir %s -> %s' % (filepath, inpath))
                    upload_dir(client, filepath, local_path)

    for syncp in syncdirlist:
        sync_folder(*syncp)


sync_thread = None
stop_evt = None

def sync(client, localpath, evt):
    assert client.is_authed()
    db = bsddb.btopen(os.path.join(get_cfg_dir(), 'hash.db'))
    global g_ind
    g_ind.set_icon(os.path.abspath("syncing.png"))
    sync_folder(client, '/', localpath, evt, db, localpath)
    g_ind.set_icon(os.path.abspath("synced.png"))
    print('sync finished')
    global sync_thread
    sync_thread = None


def time_sync(client, localpath, evt):
    while not evt.isSet():
        sync(client, localpath, evt)
        time.sleep(60)


def start_sync(client, local_path, ind, isTimes = True):
    global g_ind
    g_ind = ind
    global sync_thread
    if not sync_thread:
        global stop_evt
        stop_evt = Event()
        sync_thread = Thread(target= (time_sync if isTimes else sync), args=(client, local_path, stop_evt))
        sync_thread.start()
        return True
    else:
        print('sync thread is running')
        return False


def stop_sync():
    global stop_evt
    if stop_evt:
        stop_evt.set()
        stop_evt = None
