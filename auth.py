#! /usr/bin/env python
#coding=utf-8

import webkit
import gtk
from cfg import get_cfg_path

is_auth_exit = False
verifier = None

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


def auth(client, config):
    if client.is_authed():
        return True

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
            fp = open(get_cfg_path(), 'w')
            config.write(fp)
        elif res == False:
            print('authorize failed, try again')
            auth(client)
        else:
            print('exit authorizing')

    return client.is_authed()
