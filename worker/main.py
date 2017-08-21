#!/usr/bin/python3

import zmq, sys, io, os, youtube_dl, functools, json, contextlib, re, glob, pathlib

def main():
  print("worker-dl")
  print("pyzmq version:", zmq.pyzmq_version())

  if len(sys.argv) != 4:
    print('The correct syntax is %s address port_pull port_push' % sys.argv[0])
    sys.exit(1)

  _, address, port_pull, port_push = sys.argv
  start(address, port_pull, port_push)

def start(address, port_pull, port_push):
  context = zmq.Context()

  puller = context.socket(zmq.PULL)
  puller.connect("tcp://%s:%s" % (address, port_pull))

  pusher = context.socket(zmq.PUSH)
  pusher.connect("tcp://%s:%s" % (address, port_push))
  listen(puller, pusher)

def listen(puller, pusher):
  while True:
    try:
      msg = puller.recv_json()
    except Exception as err:
      print("Unable to decode received in the puller", err)

    try:
      pusher.send_json({'uuid': msg['uuid'], 'status': 'accepted'})
      data = None

      opts = msg['opts']
      opts['forcejson'] = True
      opts['quiet'] = True
      opts['progress_hooks'] = [functools.partial(hook, push=pusher, returned_data=data, payload=msg)]

      f = io.StringIO()
      with contextlib.redirect_stdout(f):
        with youtube_dl.YoutubeDL(msg['opts']) as ydl:
          return_code = ydl.download(msg['url'])

      if return_code == 0:
        data = json.loads('['+re.sub('}\s*{', '}, {', f.getvalue())+']')
        for d in data:
          fix_filename(d)
          pathlib.Path(d['_filename']).touch() # Fix for CRON
          pusher.send_json({'uuid': msg['uuid'], 'status': 'success', 'data': d})
      else:
        pusher.send_json({'uuid': msg['uuid'], 'status': 'fail'})

    except Exception as err:
      print(err)
      pusher.send_json({'uuid': msg['uuid'], 'status': 'fail'})

def fix_filename(d):
  if os.path.exists(d['_filename']):
    return

  without_ext = d['_filename'].rsplit('.', 1)
  found = glob.glob(without_ext[0]+'.*')
  if len(found) > 0:
    d['_filename'] = found[0]

def hook(ytl_info, push, returned_data, payload):
  if ytl_info['status'] == 'finished':
    push.send_json({
      'uuid': payload['uuid'],
      'status': 'encoding'
    })
  elif ytl_info['status'] == 'downloading':
    push.send_json({
      'uuid': payload['uuid'],
      'status': 'downloading',
      'data': {
        'elapsed': ytl_info['elapsed'],
        'eta': ytl_info['eta']
      }
    })

if __name__ == '__main__':
  main()
