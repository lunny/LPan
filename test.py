#! /usr/bin/env python
#coding=utf-8

import gtk
import webkit
from api import Client
import ConfigParser
import traceback
import os.path

verifier = ""
auth_url = ""


def _finished_loading(view, frame):
    print("_finished_loading: %s - %s" % (view, frame))
    if view.get_main_frame().get_title() == '快盘open-api':
        print("find destinated page")
        #授权错误：账号或密码错误
        html = view.get_html()
        print html
        if html.find('授权码：') > 0:
            start = html.find('<strong>')
            end = html.find('</strong>')
            global verifier
            verifier = html[start+len('<strong>'):end]
            print verifier
            gtk.mainquit()
        else:
            global auth_url
            view.load_url(auth_url)


class WebView(webkit.WebView):
    def get_html(self):
        self.execute_script('oldtitle=document.title;document.title=document.documentElement.innerHTML;')
        html = self.get_main_frame().get_title()
        self.execute_script('document.title=oldtitle;')
        return html


def _auth_closed(param):
    print('auth frame closed: %s' % param)


def authorize(client, url, param):
    view = WebView()
    view.connect('load-finished', _finished_loading)
    sw = gtk.ScrolledWindow()
    sw.connect('destroy', _auth_closed)
    sw.set_size_request(640, 420)
    sw.add(view)
    win = gtk.Window(gtk.WINDOW_TOPLEVEL)
    win.add(sw)
    win.show_all()
    view.open(url)
    gtk.main()
    return verifier


def full_test():
    _consumer_key = "xc2HkjEyY36EgLCp"
    _consumer_secret = "V7irEYzo06YSjNrA"    
    try:
        client = Client(_consumer_key, _consumer_secret)
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
            if client.auth(authorize, 'test'):
                config.add_section('authorize')
                config.set('authorize', 'oauth_token', client._oauth_token)
                config.set('authorize', 'oauth_token_secret', client._oauth_token_secret)
                config.set('authorize', 'user_id', client._user_id)
                fp = open(cf, 'w')
                config.write(fp)
            else:
                print('authorize failed')

        if client.is_authed():
            account_info = client.get_account_info()
            print account_info
            
            fileinfo = client.fileinfo('/')
            print fileinfo
    except:
        print(traceback.format_exc())    


if __name__ == "__main__":
    full_test()
