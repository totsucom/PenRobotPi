# -*- coding: utf-8 -*-
from flask import Flask, request
from flask_socketio import SocketIO
import json

from time import sleep
import threading
import serial

import VectorFontLoader       #ベクトルフォントクラス
from Polygon import Polygon   #描画エリア計算用
import random

from PIL import Image, ImageDraw
import base64


#スレッドでArduinoと通信する
class ThreadJob(threading.Thread):
  abort_task = False
  task_running = False
  vectors = []
  send_vector = 0 # 0:None 1:NeedToSend 2:WaitFor"end"
  current_x = 0
  current_y = 0
  current_l = 0
  current_r = 0
  current_u = 0
  current_pen = 0

  def __init__(self, ser, socketio):
    threading.Thread.__init__(self)
    self.ser = ser
    self.socketio = socketio

  def run(self):
    self.task_running = True

    #Arduinoの初期設定と、状態取得
    # sn,sf:ペンの高さ設定
    # j:情報はjsonで
    # i:情報要求
    self.ser.write("sn76\nsf83\nj\ni".encode('ascii'))

    write_count = 0
    write_total = 0
    x0 = 0
    y0 = 0
    try:
      while self.abort_task == False:

        #シリアルポートから読む
        s = self.ser.readline().strip()
        if len(s) > 0:

          if s[0] == "{":
            print s
            #情報取得
            info = json.loads(s)
            self.current_x = float(info['x'])
            self.current_y = float(info['y'])
            self.current_l = float(info['l'])
            self.current_r = float(info['r'])
            self.current_u = float(info['u'])
            self.current_pen = int(info['pen'])
            #ユーザーに転送
            self.socketio.emit('json', {'x':self.current_x, 'y':self.current_y, 'l':self.current_l, 'r':self.current_r, 'u':self.current_u, 'pen':self.current_pen})

          elif s == "start":
            #連続描画開始
            #ユーザーに通知
            self.socketio.emit('json', {'status': 'ビジー'})

          elif s == "end":
            if len(self.vectors) > 0:
              #連続描画継続
              self.send_vector = 1
            else:
              #連続描画完了
              self.send_vector = 0
              #ユーザーに通知
              self.socketio.emit('json', {'status': 'アイドル'})

          elif s == "align":
            #原点
            #ユーザーに通知
            self.socketio.emit('json', {'status': '原点'})

          else:
            #不明なデータ
            print "Unknown reply >>> " + s

        #シリアルポートに送信
        if self.send_vector == 1:
          if write_count == 0:
            write_total = len(self.vectors)
            if write_total > 100:
              write_total = 100
            self.ser.write(("N%d\n" % write_total).encode('ascii'))
          vu = self.vectors.pop(0)
          self.ser.write((vu.toCommand() + "\n").encode('ascii'))
          if vu.cmd == 'M':
            x0 = vu.x
            y0 = vu.y
          elif vu.cmd == 'L':
            self.socketio.emit('json', {'x1':x0 ,'y1':y0 ,'x2':vu.x, 'y2':vu.y})
            x0 = vu.x
            y0 = vu.y
          write_count += 1
          if write_total == write_count:
            self.send_vector = 2
            write_count = 0
            self.ser.write("G\n".encode('ascii'))
    except:
      import traceback
      traceback.print_exc()
    self.task_running = False
    print("task aborted!")


#ベクターフォントの初期化
vf = VectorFontLoader.VectorFontLoader("a.dict2", "a.vect2")

#書き込み可能な範囲
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

#書き込んだ範囲を記憶
wroteRectangles = []

#ユーザーと共有する仮想イメージと原点座標
canvas = None
canvas_cx = 0
canvas_cy = 0
draw = None #描画オブジェクト

#ソケットIOの初期化
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

#シリアルポートの初期化
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=0.1)

#スレッドの初期化(開始はまだ)
thread = ThreadJob(ser, socketio)


#ユーザーが接続した
@socketio.on('connect')
def handle_connect():
  global socketio
  global canvas, canvas_cx, canvas_cy
  global thread
  bs = canvas.tobytes()
  socketio.emit('json', \
    {'image': base64.b64encode(bs), 'width': canvas.size[0], 'height': canvas.size[1], 'cx': canvas_cx, 'cy': canvas_cy, 'x': thread.current_x, 'y': thread.current_y, 'pen': thread.current_pen}, \
      broadcast = False) #接続した人のみに現在の情報を送信
  #socketio.emit('json', \
  #  '{"image":"%s","width":%d,"height":%d,"cx":%f,"cy":%f,"x":%f,"y":%f,"pen":%d}' % \
  #    (base64.b64encode(bs), canvas.size[0], canvas.size[1], canvas_cx, canvas_cy, thread.current_x, thread.current_y, thread.current_pen), \
  #      broadcast = False, include_self=True) #接続した人のみに現在の情報を送信
  #json_data = { 'image': base64.b64encode(bs), 'width': canvas.size[0], 'height': canvas.size[1], 'cx':canvas_cx, 'cy':canvas_cy, 'x': thread.current_x, 'y': thread.current_y, 'pen': thread.current_pen }
  #socketio.emit('json', json.dumps(json_data), broadcast = False) #接続した人のみに現在の情報を送信
  #socketio.emit('message', 'Welcome!', broadcast=False)
  #socketio.emit('message', 'Someone connected', broadcast=True, include_self=False)

#ユーザーとの通信
@socketio.on('json')
def handle_json(json):
  global vf
  global canvas, canvas_cx, canvas_cy, draw
  global wroteRectangles
  global writableArea
  global socketio
  global thread

  if 'pen' in json:
    if json['pen'] == 0:
      ser.write("up\n".encode('ascii'))
      socketio.emit('json', {'pen':0}, broadcast = True, include_self = False)
      thread.current_pen = 0
    else:
      ser.write("dn\n".encode('ascii'))
      socketio.emit('json', {'pen':1}, broadcast = True, include_self = False)
      thread.current_pen = 1

  if 'x' in json:
    x1 = float(json['x'])
    y1 = float(json['y'])
    ser.write(("M%f,%f\n" %(x1, y1)).encode('ascii'))
    socketio.emit('json', {'x':x1, 'y':y1}, broadcast = True, include_self = False)
    thread.current_x = x1
    thread.current_y = y1

  if 'x1' in json:
    x1 = float(json['x1'])
    y1 = float(json['y1'])
    x2 = float(json['x2'])
    y2 = float(json['y2'])
    ser.write(("M%f,%f\nL%f,%f\n" %(x1, y1, x2, y2)).encode('ascii'))
    socketio.emit('json', {'x1':x1 ,'y1':y1 ,'x2':x2, 'y2':y2}, broadcast = True, include_self = False)
    draw.line((x1 + canvas_cx, y1 + canvas_cy, x2 + canvas_cx, y2 + canvas_cy), fill = (0, 0, 0), width = 1)
    thread.current_x = x2
    thread.current_y = y2

  if 'clear' in json:
    wroteRectangles = []

    w = (int)(writableArea.xmax - writableArea.xmin)
    h = (int)(writableArea.ymax - writableArea.ymin)
    canvas = Image.new('RGB', (w, h), (0xee,0xee,0xee))
    canvas_cx = w / 2 + writableArea.xmin
    canvas_cy = h / 2 + writableArea.ymin
    draw = ImageDraw.Draw(canvas)

    bs = canvas.tobytes()
    socketio.emit('json', \
      {'image': base64.b64encode(bs), 'width': canvas.size[0], 'height': canvas.size[1], 'cx': canvas_cx, 'cy': canvas_cy, 'x': thread.current_x, 'y': thread.current_y, 'pen': thread.current_pen}, \
        broadcast = False) #接続した人のみに現在の情報を送信
    #json_data = { 'image': base64.b64encode(bs), 'width': canvas.size[0], 'height': canvas.size[1], 'cx':canvas_cx, 'cy':canvas_cy, 'x': thread.current_x, 'y': thread.current_y, 'pen': thread.current_pen }
    #socketio.emit('json', json.dumps(json_data))

  if 'align' in json:
    ser.write("g\n".encode('ascii'))

  if 'text' in json:
    text = json['text']
    if len(text) > 0:
      va = vf.getVectorArrayFromText(text)
      if va.count() > 0:
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
          socketio.emit('json', {'status': 'スペースがありません'})
        else:
          socketio.emit('json', {'status': 'ビジー'}) #わかってるので早めにビジー
          
          #スレッドにベクトルを渡す
          print "draw size " + str(width * scale) + " x " + str(height * scale)
          va.scale(scale, scale)
          va.offset(rc.x, rc.y)
          for vu in va.ar:
            thread.vectors.append(vu)
          thread.send_vector = 1 #Trigger on
          wroteRectangles.append(rc)

#@socketio.on('my event')
#def handle_my_custom_event(json):
#  print('received json: ' + str(json))


if __name__ == '__main__':

  #キャンバスの準備
  w = (int)(writableArea.xmax - writableArea.xmin)
  h = (int)(writableArea.ymax - writableArea.ymin)
  canvas = Image.new('RGB', (w, h), (0xee,0xee,0xee))
  canvas_cx = -writableArea.xmin
  canvas_cy = -writableArea.ymin
  draw = ImageDraw.Draw(canvas)

  #スレッドの開始
  thread.start()


  #ソケットIOの開始（ここでブロックされる）
  socketio.run(app, host = '0.0.0.0', port = 5000, debug = False, log_output = False)


  #終了処理
  thread.abort_task = True
  print("waiting for task finish...")
  while thread.task_running == True:
    sleep(0.1)
  ser.close()
  print("server exit!")
