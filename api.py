#! /usr/bin/env python
#coding=utf-8

import urllib2, urllib, cookielib
import hmac, hashlib, base64, time, random
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import os

try:
    import simplejson as json
except ImportError: # For Python >= 2.6
    import json
    

def quote(_i):
    return urllib.quote(str(_i), "~")


def to_str(x):
    _to_str = lambda i: x if not isinstance(x, unicode) else x.encode("utf-8")
    if not isinstance(x, (str, unicode)):
        return str(x)
    return _to_str(x)


def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())


def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


def build_base_string(params, url, http_method): # Notice here the dict has been quoted twice.
    params_str_dict = [quote(k) + "=" + quote(v) for k, v in params.items()]
    params_str_dict.sort()            
    return ("%s&%s&%s" % (http_method,
                         quote(url),
                         quote("&".join(params_str_dict))))


def generate_oauth_signature(base_string, _consumer_secret, _oauth_token_secret=""):
    key = "%s&%s" % (_consumer_secret, _oauth_token_secret)
    _tmp_sig = hmac.new(key, base_string, digestmod=hashlib.sha1).digest()
    return base64.encodestring(_tmp_sig).replace("\n","")


def signature(consumer_key, consumer_secret, request_url, eparams={}, token_secret="", http_method="GET"):
    params = dict(
        oauth_consumer_key = consumer_key,
        oauth_nonce = generate_nonce(),
        oauth_signature_method = "HMAC-SHA1",
        oauth_timestamp = generate_timestamp(),
        oauth_version = "1.0",
    )
    params = dict(params, **eparams)

    _base_string = build_base_string(params, request_url, http_method)
    #print(_base_string)
    params["oauth_signature"] = generate_oauth_signature(_base_string, consumer_secret, token_secret)
    url = request_url+"?%s" % urllib.urlencode(params)
    return url


def _getResponse(url):
    req = urllib2.urlopen(url)
    return json.loads(req.read())
     

def _getResponseWithCookie(url):
     mycookie=cookielib.CookieJar()
     opener=urllib2.build_opener(urllib2.HTTPCookieProcessor(mycookie))
     req=opener.open(url)
     return req.read()


def _postFile(url, path):
     register_openers()
     datagen, headers = multipart_encode({"file": open(path, "rb")})
     request = urllib2.Request( url, datagen, headers)
     data=json.loads(urllib2.urlopen(request).read() )
     return data


class Client():
    _consumer_key = ""
    _consumer_secret = ""    
    _oauth_token = None
    _oauth_token_secret = None
    _user_id = 0


    def __init__(self, consumer_key, consumer_secret, oauth_token=None, oauth_token_secret=None):
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._oauth_token = oauth_token
        self._oauth_token_secret = oauth_token_secret


    def is_authed(self):
        return self._oauth_token and self._oauth_token_secret


    def signature(self, request_url, eparams={}, token_secret="", http_method="GET"):
        return signature(self._consumer_key, self._consumer_secret, request_url, eparams, token_secret, http_method)


    def request_token(self):
        request_token_url = 'https://openapi.kuaipan.cn/open/requestToken'
        sign_url = self.signature(request_token_url)
        return _getResponse(sign_url)


    def access_token(self, tmp_token, tmp_token_secret, verifier):
        access_token_url = "https://openapi.kuaipan.cn/open/accessToken"
        eparams = dict(oauth_token = tmp_token, oauth_verifier = verifier)
        sign_url = self.signature(access_token_url, eparams, tmp_token_secret)
        return _getResponse(sign_url)


    def set_auth(self, oauth_token, oauth_token_secret, user_id = 0):
        self._oauth_token = oauth_token
        self._oauth_token_secret = oauth_token_secret
        self._user_id = user_id


    def clear_auth(self):
        self._oauth_token = None
        self._oauth_token_secret = None
        self._user_id = 0


    def auth(self, callback, param = None):
        ret = self.request_token()
        #verifier = callback(sefl, ret)
        tmp_token = ret['oauth_token']
        tmp_token_secret = ret["oauth_token_secret"]
        url = "https://www.kuaipan.cn/api.php?ac=open&op=authorise&oauth_token=%s" % tmp_token
        verifier = callback(self, url, param) if param else callback(self, url)
        if verifier:
            newret = self.access_token(tmp_token, tmp_token_secret, verifier)
            print(newret)
            self._oauth_token = newret['oauth_token']
            self._oauth_token_secret = newret['oauth_token_secret']
            self._user_id = newret['user_id']
            return True 
        else:
            return verifier


    def request(self, url, eparams={}):
        tmpparams = dict(oauth_token = self._oauth_token)
        tmpparams = dict(tmpparams, **eparams)
        sign_url = self.signature(url, tmpparams, self._oauth_token_secret)
        return _getResponse(sign_url)


    def get_account_info(self):
        assert self.is_authed()
        return self.request('http://openapi.kuaipan.cn/1/account_info')    


    def fileinfo(self, path, root="app_folder"):
        assert self.is_authed()
        url = "http://openapi.kuaipan.cn/1/metadata/%s/%s" % (root, urllib2.quote(to_str(path)))
        return self.request(url)


    def shares(self, path, root="app_folder"):
        assert self.is_authed()
        url = "http://openapi.kuaipan.cn/1/shares/%s/%s" % (root, path)
        return self.request(url)


    def create_folder(self, path, root="app_folder"):
        assert self.is_authed()
        url = "http://openapi.kuaipan.cn/1/fileops/create_folder"
        return self.request(url, {'path': to_str(path), 'root': root})


    def delete(self, path, root="app_folder", to_recycle="True"):
        assert self.is_authed()
        url = "http://openapi.kuaipan.cn/1/fileops/delete"
        return self.request(url, {'path': to_str(path), 'root': root, 'to_recycle': to_recycle})


    def move(self, from_path, to_path, root="app_folder"):
        assert self.is_authed()
        url = 'http://openapi.kuaipan.cn/1/fileops/move'
        return self.request(url, {'from_path': to_str(from_path), 'to_path': to_str(to_path), 'root': root})


    def copy(self, from_path, to_path, root="app_folder"):
        assert self.is_authed()
        url = 'http://openapi.kuaipan.cn/1/fileops/copy'
        return self.request(url, {'from_path': to_str(from_path), 'to_path': to_str(to_path), 'root':root})


    def upload(self,path,local_path,root="app_folder",overwrite="False",ip=None):
        assert self.is_authed()
        url = 'http://api-content.dfs.kuaipan.cn/1/fileops/upload_locate'
        args1={}
        if ip:
            args1["source_ip"]=ip 

        postinfo = self.request(url, args1)

        upload_url = postinfo['url'].rstrip('/')+'/1/fileops/upload_file'
        args2={'overwrite':overwrite, 'root':root, 'path': to_str(path), 'oauth_token': self._oauth_token}
        sign_url=self.signature(upload_url.encode('utf8'), args2, self._oauth_token_secret, "POST")
        return _postFile(sign_url, local_path)


    def download(self, path, root="app_folder"):
        assert self.is_authed()
        url = 'http://api-content.dfs.kuaipan.cn/1/fileops/download_file'
        param = {'path': to_str(path),'root':root, 'oauth_token': self._oauth_token}
        link = self.signature(url, param, self._oauth_token_secret)
        print('download %s' % link)
        return _getResponseWithCookie(link)


    def thumbnail(self, path, width, height, root="app_folder"):
        assert self.is_authed()
        url = 'http://conv.kuaipan.cn/1/fileops/thumbnail'
        param = {'path':path,'root':root,'width':width,'height':height, 'oauth_token': self._oauth_token}
        link = self.signature(url, param, self._oauth_token_secret)
        return self._getResponseWithCookie(link)


    def documentView(self, path, docType, view='normal', has_zip="1", root='app_folder'):
        """
        docType=['pdf', 'doc', 'wps', 'csv', 'prn', 'xls', 'et', 'ppt', 'dps', 'txt', 'rtf']
        """
        url = 'http://conv.kuaipan.cn/1/fileops/documentView'
        param = {'type':docType,'view':view,'zip':has_zip,'path':path,'root':root, 'oauth_token': self._oauth_token}
        link = self.signature(url, param, self._oauth_token_secret)
        return self._getResponseWithCookie(link)


def upload_dir(client, dir, local_path):
    client.create_folder(dir[len(local_path):])
    for fs in os.listdir(dir):
        rfs = os.path.join(dir, fs)
        if os.path.isfile(rfs):
            client.upload(rfs[len(local_path):], rfs)
        elif os.path.isdir(rfs):
            upload_dir(client, rfs, local_path)
