# -*- coding: utf-8 -*-

from flask import Flask, render_template
from flask_socketio import SocketIO

from time import sleep
import threading
import serial

import VectorFontLoader
from Polygon import Polygon
import random

#For debug
use_serial = True


#Thread for monitioring reply from Serial port
class ThreadJob(threading.Thread):
  abort_task = False
  task_running = False
  vectors = []
  send_vector = 0 # 0:None 1:NeedToSend 2:WaitFor"END"

  def __init__(self, ser, socketio):
    threading.Thread.__init__(self)
    self.ser = ser
    self.socketio = socketio

  def run(self):
    self.task_running = True
    write_count = 0
    try:
      while self.abort_task == False:
        #Read from serial
        s = self.ser.readline()
        if len(s) > 0:
          if s[0] == "{":
            self.socketio.emit('status', s)
          else:
            if s[0] == 'E' and s[1] == 'N' and s[2] == 'D':
              if len(self.vectors) > 0:
                self.send_vector = 1
                print "CONTINUE"
              else:
                self.send_vector = 0
                print "END ALL"
            else:
              print "Read > " + s
        #Send to serial
        if self.send_vector == 1:
          if write_count >= 100 or len(self.vectors) == 0:
              self.send_vector = 2
              write_count = 0
              self.ser.write("G\n".encode('ascii'))
          else:
            vu = self.vectors.pop(0)
            self.ser.write((vu.toCommand() + "\n").encode('ascii'))
            write_count += 1
    except:
      import traceback
      traceback.print_exc()
      #print("exception occured in task!")
    self.task_running = False
    print("task aborted!")



if use_serial:
  ser = serial.Serial('/dev/ttyACM0', 115200, timeout=0.1)

vfl = VectorFontLoader.VectorFontLoader("font.dict", "font.vector")

wroteRectangles = []
writableArea = Polygon([
    0, 36.85,
    25.38, 35.32,
    47.47, 27.07,
    47.81, 57.74,
    37.69, 84.93,
    16.12, 103.95,
    0, 112.12,
    -16.47, 107.47,
    -34.24, 97.21,
    -55.76, 66.84,
    -60.64, 36.11,
    -54.13, 9.53
])

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

t = ThreadJob(ser, socketio)

#@app.route('/')
#def index():
#  with open('index.html') as f:
#    s = f.read()
#    return s

#index.htmlからコマンド受信
@socketio.on('json')
def handle_json(json):
  global vfl
  global wroteRectangles
  global writableArea
  global socketio
  global t

  #print(json['cmd'])
  if json['cmd'][0] == 'c':
    wroteRectangles = []
    socketio.emit('debug', 'reset drawing record')
  elif json['cmd'][0] == 't':
    #tの後に続く文字列を書く
    text = json['cmd'][1:]
    if len(text) > 0:
      result = vfl.getVectorArrayFromText(text)
      va = result[0] #VectorArray
      w = result[1]  #width
      h = result[2]  #height
      if w <= 0:
        socketio.emit('debug', 'nothing to draw')
      else:
        #描画位置をランダムに決定
        x = (writableArea.xmax - writableArea.xmin) * random.random() + writableArea.xmin
        y = (writableArea.ymax - writableArea.ymin) * random.random() + writableArea.ymin
        #倍率をランダムに決定
        if 30 / h < 100 / w:
          scale = 30 / h
        else:
          scale = 100 / w
        scale = (2.0 - random.random()) / 2.0 * scale

        rc = writableArea.findFreeSpace(x, y, w * scale, h * scale, wroteRectangles)
        while rc == None:
          scale *= 0.8
          if scale < 0.025:
            break
          rc = writableArea.findFreeSpace(x, y, w * scale, h * scale, wroteRectangles)

        if scale < 0.025:
          socketio.emit('debug', 'no space for draw')
        else:
          #スレッドにベクトルを渡す
          print "draw size " + str(w * scale) + " x " + str(h * scale)
          va.scale(scale, scale)
          va.offset(rc.x, rc.y)
          for vu in va.ar:
            t.vectors.append(vu)
          t.send_vector = 1 #Trigger on
          wroteRectangles.append(rc)
  else:
    if len(t.vectors) == 0:
      if use_serial:
        ser.write((json['cmd'] + "\n").encode('ascii'));

#@socketio.on('my event')
#def handle_my_custom_event(json):
#  print('received json: ' + str(json))


if __name__ == '__main__':

  #thread = threading.Thread(target=task)
  if use_serial:
    t.start()

  socketio.run(app, host='0.0.0.0', port=5000)

  if use_serial:
    t.abort_task = True
    print("waiting for task finish...")
    while t.task_running == True:
      sleep(0.1)
    ser.close()

  print("server exit!")
