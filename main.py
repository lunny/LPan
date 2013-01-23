#! /usr/bin/env python
#coding=utf-8

import gtk
import appindicator
import webbrowser
from api import Client
import os.path
from sync import start_sync, stop_sync
from monitor import start_monitor, stop_monitor
from auth import auth
from cfg import load_config, get_cfg_path


local_path = ""
g_ind = None


def openfolder(path):
    print("open the kuaipan sync folder")
    os.system('nautilus "%s"' % path)


def openwebsite(url):
    print("open the kuaipan.cn")
    webbrowser.open(url)


def size2str(size):
    ksize = size / 1024.0
    if ksize < 1:
        return "%.2f K" % ksize
    msize = ksize / 1024.0
    gsize = msize / 1024.0
    if gsize < 1:
        return "%.2f M" % msize    
    else:
        return "%.2f G" % gsize


def exit_kuaipan(param):
    print(param)

    # stop monitor thread
    stop_monitor()    
    
    #stop sync thread
    stop_sync()
    
    gtk.mainquit()


def init_indicator(ac_info, client):
    # create ubuntu indicator
    global ind
    ind = appindicator.Indicator("kuaipan",
        os.path.abspath("synced.png"), appindicator.CATEGORY_APPLICATION_STATUS)
    ind.set_status(appindicator.STATUS_ACTIVE)
    #ind.set_attention_icon("indicator-messages-new")

    # create a menu
    menu = gtk.Menu()
    namemenu = gtk.MenuItem(ac_info['user_name'])
    namemenu.show()
    menu.append(namemenu)

    spacemenu = gtk.MenuItem("已用 %s / 共 %s" % (size2str(ac_info['quota_used']), size2str(ac_info['quota_total'])))
    spacemenu.show()
    menu.append(spacemenu)
    
    blkmenu = gtk.SeparatorMenuItem()
    blkmenu.show()
    menu.append(blkmenu)    
    
    syncmenu = gtk.MenuItem("立即进行同步")
    syncmenu.connect_object("activate", local_start_sync, client)
    syncmenu.show()
    menu.append(syncmenu)
    
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
    
    exitmenu = gtk.MenuItem("退出")
    exitmenu.connect_object("activate", exit_kuaipan, None)
    exitmenu.show()
    menu.append(exitmenu)
    
    # add menu to indicator
    ind.set_menu(menu)
    return ind


def local_start_sync(client):
    global local_path
    global g_ind
    start_sync(client, local_path, g_ind, False)


def main():
    # load config
    config = load_config()
    _consumer_key = ""
    _consumer_secret = ""
    
    if config.has_section('client'):
        _consumer_key = config.get('client', '_consumer_key')
        _consumer_secret = config.get('client', '_consumer_secret')

    # init client
    client = Client(_consumer_key, _consumer_secret)
    
    # auth before use
    auth(client, config)

    if client.is_authed():
        global local_path
        global g_ind
        if config.has_section('sync'):
            local_path = config.get('sync', 'local_path')
        if not local_path:
            home_dir = os.path.expanduser('~')
            default_dir = os.path.join(home_dir, "kuaipan")
            is_create_default = False
            if not os.path.exists(default_dir):
                is_create_default = True
                os.mkdir(default_dir)
            
            dialog = gtk.FileChooserDialog(title="请选择快盘文件同步到本地存放的文件夹", parent=None,
                action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN,gtk.RESPONSE_OK))
            dialog.set_current_folder(default_dir)

            filter = gtk.FileFilter()
            filter.set_name("所有文件夹")
            filter.add_pattern("*")
            dialog.add_filter(filter)            
                
            response = dialog.run()
            if response == gtk.RESPONSE_OK:
                print dialog.get_filename(), 'selected'
                local_path = dialog.get_filename()
                if is_create_default and local_path != default_dir:
                    os.rmdir(default_dir)
                config.add_section('sync')
                config.set('sync', 'local_path', local_path)
                fp = open(get_cfg_path(), 'w')
                config.write(fp)                    
            else:
                print 'Closed, no files selected'
            dialog.destroy()

        if not local_path:
            return

        ac_info = client.get_account_info()
        print('is authed')
        print(ac_info)
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        g_ind = init_indicator(ac_info, client)

        # start sync thread
        start_sync(client, local_path, g_ind)
        
        # start monitor thread
        start_monitor(client, local_path, g_ind)
        
        # start run application
        gtk.main()
    else:
        print('not authed')


if __name__ == "__main__":
    main()
