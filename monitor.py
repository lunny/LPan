#! /usr/bin/env python
#coding=utf-8

import pyinotify
from threading import Thread, Event
from api import upload_dir
from urllib2 import HTTPError

monitor_black_list = set([])
notifier = None
m_thread = None
stop_evt = None
g_client = None
g_local_path = None
g_move_from = None
mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE | \
    pyinotify.IN_MODIFY | pyinotify.IN_MOVED_FROM | pyinotify.IN_MOVED_TO | \
    pyinotify.IN_MOVE_SELF | pyinotify.IN_IGNORED | pyinotify.IN_DELETE_SELF | \
    pyinotify.IN_ATTRIB


class EventHandler(pyinotify.ProcessEvent):


    def process_IN_CREATE(self, event):
        evtmask = event.maskname.split('|')
        if event.pathname in monitor_black_list:
            monitor_black_list.discard(event.pathname)
            return

        global g_local_path
        rpath = event.pathname[len(g_local_path):]
        if 'IN_ISDIR' in evtmask:
            global g_client
            print('create dir %s -> %s' % (event.pathname, rpath))
            g_client.create_folder(rpath)
        else:
            print('create file %s -> %s' % (event.pathname, rpath))
            g_client.upload(rpath, event.pathname)


    def process_IN_DELETE(self, event):
        evtmask = event.maskname.split('|')
        if event.pathname in monitor_black_list:
            monitor_black_list.discard(event.pathname)
            return

        global g_client
        global g_local_path
        rpath = event.pathname[len(g_local_path):]
        finfo = None
        try:
            finfo = g_client.fileinfo(rpath)
        except HTTPError:
            print('get file or dir info failed, file is not found or server error')
        
        if finfo:
            if 'IN_ISDIR' in evtmask:
                print('delete dir %s -> %s' % (event.pathname, rpath))
                if finfo['type'] != 'folder':
                    print('data type is not the same, local is dir and server is file')
                else:
                    g_client.delete(rpath)
            else:
                print('delete file %s -> %s' % (event.pathname, rpath))
                if finfo['type'] == 'folder':
                    print('data type is not the same, local is file and server is dir')
                else:
                    g_client.delete(rpath)

    def process_IN_CLOSE_WRITE(self, event):
        evtmask = event.maskname.split('|')
        if event.pathname in monitor_black_list:
            monitor_black_list.discard(event.pathname)
            return

        global g_local_path
        rpath = event.pathname[len(g_local_path):]        
        if 'IN_ISDIR' in evtmask:
            print('close write dir %s' % event.pathname)
        else:
            print('close write file %s' % event.pathname)
            print('upload file %s -> %s and overwrite' % (event.pathname, rpath))
            g_client.upload(rpath, event.pathname, root="app_folder", overwrite="True")

    def process_IN_MODIFY(self, event):
        evtmask = event.maskname.split('|')
        if event.pathname in monitor_black_list:
            monitor_black_list.discard(event.pathname)
            return

        if 'IN_ISDIR' in evtmask:
            print('modify dir %s' % event.pathname)
        else:
            print('modify file %s' % event.pathname)
        
    def process_IN_MOVED_FROM(self, event):
        evtmask = event.maskname.split('|')
        if event.pathname in monitor_black_list:
            monitor_black_list.discard(event.pathname)
            return

        global g_client
        global g_local_path
        global g_move_from
        if 'IN_ISDIR' in evtmask:
            print('move dir %s' % event.pathname)
            g_move_from = event.pathname[len(g_local_path):]
        else:
            print('move file %s' % event.pathname)
            g_move_from = event.pathname[len(g_local_path):]
    
    def process_IN_MOVED_TO(self, event):
        evtmask = event.maskname.split('|')
        if event.pathname in monitor_black_list:
            monitor_black_list.discard(event.pathname)
            return

        global g_client
        global g_local_path
        global g_move_from
        rpath_to = event.pathname[len(g_local_path):]
        if 'IN_ISDIR' in evtmask:
            print('paste dir %s' % event.pathname)
            if g_move_from:
                print('move dir %s -> %s' % (g_move_from, rpath_to))
                g_client.move(g_move_from, rpath_to)
                g_move_from = None
            else:
                print('upload dir %s -> %s' % (event.pathname, rpath_to))
                upload_dir(g_client, event.pathname, g_local_path)
        else:
            print('paste file %s' % event.pathname)
            if g_move_from:
                print('move file %s -> %s' % (g_move_from, rpath_to))
                g_client.move(g_move_from, rpath_to)
                g_move_from = None
            else:
                print('upload file %s -> %s' % (event.pathname, rpath_to))
                g_client.upload(rpath_to, event.pathname)


def monitor(client, local_path, stop_evt):
    print('start monitoring %s' % local_path)
    global g_client
    g_client = client
    global g_local_path
    g_local_path = local_path

    wm = pyinotify.WatchManager()
    handler = EventHandler()
    global notifier
    notifier = pyinotify.Notifier(wm, handler)
    wdd = wm.add_watch(local_path, mask, rec=True, auto_add=True)

    while True:
        if stop_evt.isSet():
            notifier.stop()
            break

        notifier.process_events()
        if notifier.check_events(timeout=1000):
            notifier.read_events()

    m_thread = None
    print('stop monitoring %s' % local_path)


def start_monitor(client, local_path):
    global m_thread
    if not m_thread:
        global stop_evt
        stop_evt = Event()
        m_thread = Thread(target=monitor, args=(client, local_path, stop_evt))
        m_thread.start()
        return True
    else:
        print('monitor thread is running')
        return False


def stop_monitor():
    global m_thread
    if m_thread:
        stop_evt.set()
