# -*- coding: utf-8 -*-
from flask import Flask, request
from flask_socketio import SocketIO
import json

from time import sleep
import threading
import serial
import struct                 #シリアル通信用バイナリデータ作成
from collections import deque #キュー

import VectorFontLoader       #ベクトルフォントクラス
from Polygon import Polygon   #描画エリア計算用
import random

from PIL import Image, ImageDraw
import base64

import math

#Arduinoに送信するデータを保持するクラス
class Command:
  cmd = 0  #シリアルポート送信コマンド  
  f1 = 0.0
  f2 = 0.0

  def __init__(self, cmd, f1=1.7976931348623157e+308, f2=1.7976931348623157e+308):
    self.cmd = cmd
    self.f1 = f1
    self.f2 = f2

  def getbytes(self):
    if self.f2 != 1.7976931348623157e+308:
      return struct.pack("<BBff", 255, self.cmd, self.f1, self.f2)
    elif self.f1 != 1.7976931348623157e+308:
      return struct.pack("<BBf", 255, self.cmd, self.f1)
    else:
      return struct.pack("<BB", 255, self.cmd)


#スレッドでArduinoと通信するクラス
class ThreadJob(threading.Thread):
  abort_task = False
  task_running = False

  #Arduinoにシリアル送信するCommandクラスをキューする
  cmd_que = deque()

  def __init__(self, g):
    threading.Thread.__init__(self)
    self.g = g

  def run(self):
    self.task_running = True

    #Arduinoの初期設定と、状態取得
    # sn,sf:ペンの高さ設定
    # i:情報要求
    self.g.ser.write(struct.pack("<BBf", 255, self.g.cmd_set_near_angle, 76.0))
    self.g.ser.write(struct.pack("<BBf", 255, self.g.cmd_set_far_angle, 83.0))
    self.g.ser.write(struct.pack("<BB", 255, self.g.cmd_info))

    x0 = 0
    y0 = 0

    try:
      while self.abort_task == False:

        if len(self.cmd_que) > 0:
          c = self.cmd_que.popleft() #c=Commandクラス

          if c.cmd == self.g.cmd_move_to:
            dist = math.sqrt((x0 - c.f1) * (x0 - c.f1) + (y0 - c.f2) * (y0 - c.f2))
            if dist >= 1.0: #あまりに近い移動コマンドは無視
              #シリアルポートに送信
              self.g.ser.write(c.getbytes())

              #ペン位置をユーザーに知らせる
              self.g.socketio.emit('json', {'x':c.f1 ,'y':c.f2})

              #print "move vec " + str(c.f1-x0) + ", " + str(c.f2-y0)


              x0 = c.f1
              y0 = c.f2

          else:
            #シリアルポートに送信
            self.g.ser.write(c.getbytes())

            if c.cmd == self.g.cmd_line_to:
              #線の描画をユーザーに指示
              self.g.socketio.emit('json', {'x1':x0 ,'y1':y0 ,'x2':c.f1, 'y2':c.f2})
              #保持している画像も更新
              self.g.draw.line((x0 + self.g.cx, y0 + self.g.cy, c.f1 + self.g.cx, c.f2 + self.g.cy), fill = (255), width = 1)

              print "line vec " + str(c.f1-x0) + ", " + str(c.f2-y0)

              x0 = c.f1
              y0 = c.f2

        #シリアルポートから読む
        s = self.g.ser.readline()
        if len(s) > 0:
          s = s.strip()
        if len(s) > 0:

          if s[0] == "{":
            print s
            j = json.loads(s)
            self.g.socketio.emit('json', j)
            if 'x' in j:
              self.g.current_x = float(j['x'])
              self.g.current_y = float(j['y'])

          else:
            #不明なデータ
            print ">>> " + s

    except:
      import traceback
      traceback.print_exc()
    self.task_running = False
    self.g.socketio.emit('json', {'status': 'TASK ABORTED!'})
    print("task aborted!")

class GlovalVars:
  #シリアルポート送信コマンド Python2にはenumが無いw
  ( cmd_move_x,          # <f>　　　ペンをX方向に相対移動する 単位[mm]  例 x-1.5
    cmd_move_y,          # <f>　　　ペンをY方向に相対移動する 単位[mm]
    cmd_angle_l,         # <f>　　　左サーボを相対回転する　　単位[度]
    cmd_angle_r,         # <f>　　　右サーボを相対回転する　　単位[度]
    cmd_angle_u,         # <f>　　　上下サーボを相対回転する　単位[度]
    cmd_move_to_near,    #  　　　　ペンの位置を近距離側へ移動(snコマンド用)
    cmd_set_near_angle,  # <f>　　 上下サーボの近距離側のペンの書く高さを絶対角度で設定する　単位[度]
    cmd_move_to_far,     # 　　　　 ペンの位置を遠距離側へ移動(sfコマンド用)
    cmd_set_far_angle,   # <f>　　 上下サーボの遠距離側のペンの書く高さを絶対角度で設定する　単位[度]
    cmd_pen_up,          # 　　　　 ペンを上げる
    cmd_pen_down,        # 　　　　 ペンを下げる（書くポジション）
    cmd_move_to,         # <f><f>  ペンを上げた状態で絶対座標に移動する　　　　単位[mm]　例 m-20,50.5
    cmd_line_to,         # <f><f>  ペンを下げた状態で絶対座標に移動する（書く）
    cmd_align,           # 　　　　　ペンを上げて原点位置に戻る
    cmd_info             # 　　　　　角度や座標の情報を表示
  ) = range(128, 143)

  socketio = None  
  ser = None
  thread = None
  vf = None
  writableArea = None
  wroteRectangles = [] #書き込んだ範囲を記憶
  
  #ペン位置
  current_x = 0
  current_y = 0

  #ユーザーと共有する仮想イメージと原点座標
  canvas = None
  cx = 0
  cy = 0
  draw = None


#グローバル変数をまとめて保持
g = GlovalVars()

#ベクターフォントの初期化
g.vf = VectorFontLoader.VectorFontLoader("a.dict2", "a.vect2")

#書き込み可能な範囲
g.writableArea = Polygon([0, 36.85,  25.38, 35.32,  47.47, 27.07,  47.81, 57.74,  37.69, 84.93,  16.12, 103.95,  0, 112.12,  -16.47, 107.47,  -34.24, 97.21,  -55.76, 66.84,  -60.64, 36.11,  -54.13, 9.53])

#ソケットIOの初期化
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
g.socketio = SocketIO(app)

#シリアルポートの初期化
g.ser = serial.Serial('/dev/ttyACM0', 115200, timeout=0.01)

#スレッドの初期化(開始はまだ)
g.thread = ThreadJob(g)


#キャンバスの準備
def new_canvas():
  global g
  g.wroteRectangles = []

  w = (int)(g.writableArea.xmax - g.writableArea.xmin) + 1
  h = (int)(g.writableArea.ymax - g.writableArea.ymin) + 1
  g.canvas = Image.new('L', (w, h))  # L=1pixel/byte(0 or 255), filled by black = 0
  g.cx = -g.writableArea.xmin
  g.cy = -g.writableArea.ymin
  g.draw = ImageDraw.Draw(g.canvas)

  #枠線
  #p0 = g.writableArea.points[-1]
  #for i in range(len(g.writableArea.points)):
  #  p1 = g.writableArea.points[i]
  #  g.draw.line((p0.x + g.cx, p0.y + g.cy, p1.x + g.cx, p1.y + g.cy), fill = (0, 255, 0), width = 1)
  #  p0 = p1



#ユーザーが接続した
@g.socketio.on('connect')
def handle_connect():
  global g
  bs = g.canvas.tobytes()
  
  #接続した人のみに現在の情報を送信しているはずだが、ほかにも飛んでくw
  g.socketio.emit('json', {
    'image': base64.b64encode(bs),
    'width': g.canvas.size[0], 'height': g.canvas.size[1],
    'cx': g.cx, 'cy': g.cy,
    'x': g.current_x, 'y': g.current_y
    }, broadcast = False)

#ユーザーとの通信
@g.socketio.on('json')
def handle_json(json):
  global g

  #カーソル移動
  if 'x' in json:
    g.thread.cmd_que.append(Command(g.cmd_move_to, float(json['x']), float(json['y'])))

  #線を引く
  elif 'x1' in json:
    g.thread.cmd_que.append(Command(g.cmd_move_to, float(json['x1']), float(json['y1'])))
    g.thread.cmd_que.append(Command(g.cmd_line_to, float(json['x2']), float(json['y2'])))

  #移動と線引き配列
  elif 'ar' in json:
    for cmd in json['ar']:
      if 'x' in cmd:
        #カーソル移動
        g.thread.cmd_que.append(Command(g.cmd_move_to, float(cmd['x']), float(cmd['y'])))
      #線を引く
      elif 'x1' in cmd:
        g.thread.cmd_que.append(Command(g.cmd_move_to, float(cmd['x1']), float(cmd['y1'])))
        g.thread.cmd_que.append(Command(g.cmd_line_to, float(cmd['x2']), float(cmd['y2'])))


  #紙の交換（描画履歴のクリア）
  elif 'clear' in json:
    new_canvas()
    bs = g.canvas.tobytes()

    g.socketio.emit('json', {
      'image': base64.b64encode(bs),
      'width': g.canvas.size[0], 'height': g.canvas.size[1],
      'cx': g.cx, 'cy': g.cy,
      'x': g.current_x, 'y': g.current_y
      }, broadcast = True)

  elif 'align' in json:
    g.thread.cmd_que.append(Command(g.cmd_align))

  elif 'text' in json:
    text = json['text']
    if len(text) > 0:

      #テキストを描画するベクトルを取得
      #フォントの基準高さは1.0
      va = g.vf.getVectorArrayFromText(text)
      if va.count() > 0:

        #周辺の余計な余白を除く
        bound = va.getBound()
        va.offset(-bound[0], -bound[1])
        width = bound[2] - bound[0] + 1
        height = bound[3] - bound[1] + 1

        #描画位置をランダムに決定
        x = (g.writableArea.xmax - g.writableArea.xmin) * random.random() + g.writableArea.xmin
        y = (g.writableArea.ymax - g.writableArea.ymin) * random.random() + g.writableArea.ymin

        #倍率をランダムに決定
        scale = random.random() * 20.0 + 10.0 #height 10-30mm

        #スケールを下げながら空きスペースを探す
        rc = g.writableArea.findFreeSpace(x, y, width * scale, height * scale, g.wroteRectangles)
        while rc == None:
          scale *= 0.8     #scale 80% when no space
          if scale < 10.0: #minimum 10mm height
            break
          rc = g.writableArea.findFreeSpace(x, y, width * scale, height * scale, g.wroteRectangles)

        if scale < 10.0:
          g.socketio.emit('json', {'status': 'スペースがありません'})
        else:
          g.socketio.emit('json', {'status': 'ビジー'}) #わかってるので早めにビジー
          
          #スレッドに渡す
          print "draw size " + str(width * scale) + " x " + str(height * scale)
          va.scale(scale, scale)
          va.offset(rc.x, rc.y)
          for vu in va.ar:
            if vu.cmd == 'M':
              g.thread.cmd_que.append(Command(g.cmd_move_to, vu.x, vu.y))
            elif vu.cmd == 'L':
              g.thread.cmd_que.append(Command(g.cmd_line_to, vu.x, vu.y))
          g.wroteRectangles.append(rc)


if __name__ == '__main__':

  #キャンバスの準備
  new_canvas()

  #スレッドの開始
  g.thread.start()

  #ソケットIOの開始（ここでブロックされる）
  g.socketio.run(app, host = '0.0.0.0', port = 5000) #, debug = True)


  #終了処理
  g.thread.abort_task = True
  print("waiting for task finish...")
  while g.thread.task_running == True:
    sleep(0.1)
  g.ser.close()
  print("server exit!")
