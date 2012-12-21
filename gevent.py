#! /usr/bin/python2.7
# -- coding:utf-8 --
#可以参考我的博客：http://www.cnblogs.com/descusr
 
 import urllib,urllib2,gevent,re
 from gevent import monkey
 
 
 monkey.patch_all()
 
 def worker(reg, url):
     response=urllib.urlopen(url)
     text=response.read()
     groups=re.finditer(reg, text)
     m_arr = []
     for g in groups:
         name=g.group(1).strip() + ".mp3"
         path=g.group(2).replace('\\', '')
         m_arr.append((name, path))
     return m_arr
 
 def grun(path, name):
     urllib.urlretrieve(path, name)
                                                                                                                                                       
 if __name__ == '__main__':
     #匹配音乐url
     reg=re.compile('{"name":"(.+?)".+?"rawUrl":"(.+?)",.+?}', re.I)    
     musicArray = worker(reg, "http://site.douban.com/huazhou/")
     jobs = []
     for (name, path) in musicArray:
         jobs.append(gevent.spawn(grun, path, name))
     gevent.joinall(jobs)