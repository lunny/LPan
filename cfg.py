#! /usr/bin/env python
#coding=utf-8

import os
import ConfigParser


def get_cfg_dir():
    homedir = os.path.expanduser('~')
    appcfgdir = os.path.join(homedir, ".lpan")
    if not os.path.exists(appcfgdir):
        os.mkdir(appcfgdir)
    return appcfgdir


def get_cfg_path():
    return os.path.join(get_cfg_dir(), 'config.ini')    


def load_config():
    cf = get_cfg_path()
    if not os.path.exists(cf):
        f = open(cf, 'w')
        f.close()    

    config = ConfigParser.ConfigParser()
    config.read(cf)
    return config
