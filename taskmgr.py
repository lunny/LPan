#! /usr/bin/env python
#coding=utf-8

from threading import Thread, Lock

tasks = {}
count = 0
pennding, running, pause, done, error = range(5)
l = Lock()
max_thread = 3


def add_task(type, params):
    global tasks, l, count
    l.acquire()
    count = count + 1
    id = count
    tasks[id] = [(type, params), pennding]
    l.release()
    return id


def cacel_task(taskid):
    global tasks, l
    l.acquire()
    del tasks[taskid]
    l.release()


threads = {}


def downing(client, task):
    params = task[0][1]
    try:
        data = client.download(params['path'])
        f = open(params['localpath'], 'wb')
        f.write(data)
        f.close()
        task[1] = done
        #db[path_key] = file['sha1']
    except:
        task[1] = error


def uploading(client, task):
    params = task[0][1]
    try:
        client.upload(params['path'], params['localpath'], root="app_folder", overwrite=params['overwrite'])
        #db[path_key] = file['sha1']
        task[1] = done
    except:
        task[1] = error


def start_task(client, task_id):
    task = tasks[task_id]
    type = task[0][0]
    if type == 'download':
        threads[task_id] = Thread(target=downing, args=(client, task))
    elif type == 'upload':
        threads[task_id] = Thread(target=uploading, args=(client, task))
    else:
        assert False
    tasks[task_id][1] = running
    threads[task_id].start()        


def stop_task():
    pass


def run(client, event):
    for id, task in task.iteritems():
        if evt.isSet():
            break
        if len(threads.keys()) < max_thread:
            status = task[1]
            if status == pennding:
                start_task(client, id)


def pause():
    pass


def stop():
    pass
