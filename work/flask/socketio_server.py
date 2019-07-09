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
  send_vector = 0 # 0:None 1:NeedToSend 2:WaitFor"end"

  def __init__(self, ser, socketio):
    threading.Thread.__init__(self)
    self.ser = ser
    self.socketio = socketio

  def run(self):
    self.task_running = True

    #j:information by json format
    #sn,sf:adjust pen height for write
    self.ser.write("j\nsn76\nsf83".encode('ascii'))

    write_count = 0
    write_total = 0
    try:
      while self.abort_task == False:
        #Read from serial
        s = self.ser.readline().strip()
        if len(s) > 0:
          if s[0] == "{": #information from Arduino
            self.socketio.emit('status', s)
          elif s == "start":
            print "START"
          elif s == "end":
            if len(self.vectors) > 0:
              self.send_vector = 1
              print "CONTINUE"
            else:
              self.send_vector = 0
              print "END ALL"
          elif s == "align":
            print "BACK To ALIGIN"
          else:
            print "Unknown reply > " + s
        #Send to serial
        if self.send_vector == 1:
          if write_count == 0:
            write_total = len(self.vectors)
            if write_total > 100:
              write_total = 100
            self.ser.write(("N" + str(write_total) + "\n").encode('ascii'))
          vu = self.vectors.pop(0)
          self.ser.write((vu.toCommand() + "\n").encode('ascii'))
          write_count += 1
          if write_total == write_count:
            self.send_vector = 2
            write_count = 0
            self.ser.write("G\n".encode('ascii'))
    except:
      import traceback
      traceback.print_exc()
      #print("exception occured in task!")
    self.task_running = False
    print("task aborted!")



if use_serial:
  ser = serial.Serial('/dev/ttyACM0', 115200, timeout=0.1)

vfl = VectorFontLoader.VectorFontLoader("a.dict2", "a.vect2")

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
      va = vfl.getVectorArrayFromText(text)
      if va.count() <= 0:
        socketio.emit('debug', 'nothing to draw')
      else:
        #remove extra margin
        bound = va.getBound()
        va.offset(-bound[0], -bound[1])
        width = bound[2] - bound[0] + 1
        height = bound[3] - bound[1] + 1

        #font standard height is 1.0.
        #but now height is slightly smaller than 1.0,
        #because extra margin removed.

        #描画位置をランダムに決定
        x = (writableArea.xmax - writableArea.xmin) * random.random() + writableArea.xmin
        y = (writableArea.ymax - writableArea.ymin) * random.random() + writableArea.ymin
        #倍率をランダムに決定
        scale = random.random() * 20.0 + 10.0 #height 10-30mm

        rc = writableArea.findFreeSpace(x, y, width * scale, height * scale, wroteRectangles)
        while rc == None:
          scale *= 0.8     #scale 80% when no space
          if scale < 10.0: #minimum 10mm height
            break
          rc = writableArea.findFreeSpace(x, y, width * scale, height * scale, wroteRectangles)

        if scale < 10.0:
          socketio.emit('debug', 'no space for draw')
        else:
          #スレッドにベクトルを渡す
          print "draw size " + str(width * scale) + " x " + str(height * scale)
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

  socketio.run(app, host = '0.0.0.0', port = 5000)

  if use_serial:
    t.abort_task = True
    print("waiting for task finish...")
    while t.task_running == True:
      sleep(0.1)
    ser.close()

  print("server exit!")
