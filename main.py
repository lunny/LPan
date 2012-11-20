#! /usr/bin/env python
#coding=utf-8

import gtk
import appindicator
import webkit
import webbrowser
from api import Client
import ConfigParser
import os.path

_consumer_key = "xc2HkjEyY36EgLCp"
_consumer_secret = "V7irEYzo06YSjNrA"

client = Client(_consumer_key, _consumer_secret)
verifier = None
local_path = ""


def openfolder(path):
    print("open the kuaipan sync folder")
    os.system('nautilus "%s"' % path)


def openwebsite(url):
    print("open the kuaipan.cn")
    webbrowser.open(url)


is_auth_exit = False

def _finished_loading(view, frame):
    print("_finished_loading: %s - %s" % (view, frame))
    if view.get_main_frame().get_title() == '快盘open-api':
        print("find destinated page")
        html = view.get_html()
        print html
        if html.find('授权码：') > 0:
            start = html.find('<strong>')
            end = html.find('</strong>')
            global verifier
            verifier = html[start+len('<strong>'):end]
            print verifier
        else:
            #授权错误：账号或密码错误
            verifier = False

        #关闭view对应的窗口
        pwin = view.get_parent()
        print(pwin)
        ptopwin = pwin.get_parent()
        #pwin.destroy()
        print(ptopwin)
        ptopwin.destroy()
        gtk.mainquit()


class WebView(webkit.WebView):
    def get_html(self):
        self.execute_script('oldtitle=document.title;document.title=document.documentElement.innerHTML;')
        html = self.get_main_frame().get_title()
        self.execute_script('document.title=oldtitle;')
        return html


def _auth_closed(pwin):
    print('auth frame closed: %s' % pwin)
    ptopwin = pwin.get_parent()
    #pwin.destroy()
    print(ptopwin)
    if ptopwin:
        ptopwin.destroy()
    gtk.mainquit()    

import time

def authorize(client, url):
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    view = WebView()
    view.connect('load-finished', _finished_loading)
    sw = gtk.ScrolledWindow()
    sw.connect('destroy', _auth_closed)
    sw.set_size_request(640, 420)
    sw.add(view)

    window.add(sw)
    window.show_all()
    view.open(url)

    gtk.main()
    global verifier
    
    return verifier


def auth():
    global client
    if client.is_authed():
        return True

    cf = 'config.ini'
    if not os.path.exists(cf):
        f = open(cf, 'w')
        f.close()

    config = ConfigParser.ConfigParser()
    config.read(cf)
    if config.has_section('authorize'):
        oauth_token = config.get('authorize', 'oauth_token')
        oauth_token_secret = config.get('authorize', 'oauth_token_secret')
        user_id = config.getint('authorize', 'user_id')
        print 'read token, oauth_token = %s' % oauth_token
        print 'oauth_token_secret = %s' % oauth_token_secret
        print 'user_id = %d' % user_id
        client.set_auth(oauth_token, oauth_token_secret, user_id)
        
    if not client.is_authed():
        res = client.auth(authorize)
        if res:
            config.add_section('authorize')
            config.set('authorize', 'oauth_token', client._oauth_token)
            config.set('authorize', 'oauth_token_secret', client._oauth_token_secret)
            config.set('authorize', 'user_id', client._user_id)
            fp = open(cf, 'w')
            config.write(fp)
        elif res == False:
            print('authorize failed, try again')
            auth()
        else:
            print('exit authorizing')

    return client.is_authed()

import traceback
import urllib

def sync_folder(path, localpath, evt):
    print('begin sync %s -> %s' % (path, localpath))
    global client
    fileinfo = client.fileinfo(path)
    for file in fileinfo['files']:
        if evt.isSet():
            break
        if not file['is_deleted']:
            lpath = os.path.join(localpath, file['name'])
            rpath = os.path.join(path, file['name'])
            if file['type'] == 'folder':
                if not os.path.exists(lpath):
                    print('mkdir %s' % lpath)
                    os.mkdir(lpath)
                sync_folder(rpath, lpath, evt)
            else:
                if not os.path.exists(lpath):
                    try:
                        print('begin download %s -> %s' % (rpath, lpath))
                        data = client.download(rpath[1:])
                        f = open(lpath, 'wb')
                        f.write(data)
                        f.close()
                    except:
                        print(traceback.format_exc())
                else:
                    print("%s is exist, compare file's last modified time and size" % lpath)
                
                pass
        else:
            print 'delete file: %s' % file
        

def sync(client, localpath, evt):
    assert client.is_authed()
    sync_folder('/', localpath, evt)
    print('sync finished')


def monitor():
    pass


def size2str(size):
    ksize = size / 1024
    if ksize < 1:
        return "%.2f K" % ksize
    msize = ksize / 1024
    gsize = msize / 1024
    if gsize < 1:
        return "%.2f M" % msize    
    else:
        return "%.2f G" % gsize

def init_indicator(ac_info):
    # create ubuntu indicator
    ind = appindicator.Indicator("kuaipan",
        "/media/truecrypt1/projects/lpan/logo.png", appindicator.CATEGORY_APPLICATION_STATUS)
    ind.set_status(appindicator.STATUS_ACTIVE)
    ind.set_attention_icon("indicator-messages-new")

    # create a menu
    menu = gtk.Menu()
    namemenu = gtk.MenuItem(ac_info['user_name'])
    namemenu.show()
    menu.append(namemenu)
    
    spacemenu = gtk.MenuItem("%s/%s" % (size2str(ac_info['quota_used']), size2str(ac_info['quota_total'])))
    spacemenu.show()
    menu.append(spacemenu)
    
    openmenu = gtk.MenuItem("打开快盘")
    global local_path
    openmenu.connect_object("activate", openfolder, local_path)
    openmenu.show()
    menu.append(openmenu)
    
    urlmenu = gtk.MenuItem("打开快盘网站")
    url = "http://kuaipan.cn"
    urlmenu.connect_object("activate", openwebsite, url)
    urlmenu.show()
    menu.append(urlmenu)    
    
    exitmenu = gtk.MenuItem("退出快盘")
    exitmenu.connect_object("activate", gtk.mainquit, None)
    exitmenu.show()
    menu.append(exitmenu)
    
    # add menu to indicator
    ind.set_menu(menu)
    return ind

from threading import Thread, Event

def main():
    # create window
    auth()

    global client
    if client.is_authed():
        global local_path
        local_path = "/home/lunny/kuaipan"
        ac_info = client.get_account_info()
        print('is authed')
        print(ac_info)
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        ind = init_indicator(ac_info)
        evt = Event()
        sync_thread = Thread(target=sync, args=(client, local_path, evt))
        sync_thread.start()
        gtk.main()

        evt.set()
    else:
        print('not authed')


if __name__ == "__main__":
    main()
