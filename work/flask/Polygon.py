# -*- coding: utf-8 -*-

import math

class Polygon:
  points = []
  xmin = 0
  xmax = 0
  ymin = 0
  ymax = 0

  #pointsはintまたはfloat配列。x,yの順
  #最初と最後の点は結ばなくてよい
  def __init__(self, points):
    if (len(points) & 1) == 1:
      raise ValueError("Points must even number (because X,Y)")
    self.points = []
    for i in range(len(points) / 2):
      x = points[i * 2]
      y = points[i * 2 + 1]
      self.points.append(PointXY(x, y))
      if i == 0:
        self.xmin = self.xmax = x
        self.ymin = self.ymax = y
      else:
        if x < self.xmin:
          self.xmin = x
        if x > self.xmax:
          self.xmax = x
        if y < self.ymin:
          self.ymin = y
        if y > self.ymax:
          self.ymax = y
  
  #Line(a->b),Line(c->d)
  #a..dはPointXY型
  #@staticmethod
  #def __isLineCrossing(a, b, c, d):
  #  ta = (c.x - d.x) * (a.y - c.y) + (c.y - d.y) * (c.x - a.x)
  #  tb = (c.x - d.x) * (b.y - c.y) + (c.y - d.y) * (c.x - b.x)
  #  tc = (a.x - b.x) * (c.y - a.y) + (a.y - b.y) * (a.x - c.x)
  #  td = (a.x - b.x) * (d.y - a.y) + (a.y - b.y) * (a.x - d.x)
  #  #return tc * td < 0 and ta * tb < 0 #端点を含まない
  #  return tc * td <= 0 and ta * tb <= 0 #端点を含む

  #Yにおけるポリゴンの範囲内のX範囲をRange1D配列で返す。空の場合がある
  #rectsには範囲をマスクするRectangles配列を指定することができる
  def getRangeAtY(self, y, rects=None):
    if rects != None:
      return self.__getRangeAtY(y, rects)

    ar = [] #array of int
    for i in range(len(self.points) - 1):
      if (self.points[i + 1].y >= self.points[i].y and self.points[i + 1].y >= y and y >= self.points[i].y) or \
         (self.points[i + 1].y < self.points[i].y and self.points[i + 1].y <= y and y <= self.points[i].y):
        x = (y - self.points[i].y) / (self.points[i + 1].y - self.points[i].y) * (self.points[i + 1].x - self.points[i].x) + self.points[i].x
        x = int(x + 0.5)
        if (x in ar) == False:
          ar.append(x)
    if len(self.points) >= 2:
      if (self.points[0].y >= self.points[-1].y and self.points[0].y >= y and y >= self.points[-1].y) or \
         (self.points[0].y < self.points[-1].y and self.points[0].y <= y and y <= self.points[-1].y):
        x = (y - self.points[-1].y) / (self.points[0].y - self.points[-1].y) * (self.points[0].x - self.points[-1].x) + self.points[-1].x
        x = int(x + 0.5)
        if (x in ar) == False:
          ar.append(x)
    if (len(ar) & 1) == 1:
      return []
    ar2 = []
    for i in range(0, len(ar), 2):
      ar2.append(Range1D(ar[i], ar[i + 1]))
    return ar2

  #Yにおけるポリゴンの範囲内のX範囲をRange1D配列で返す。空の場合がある
  def __getRangeAtY(self, y, rects):
    ar = []
    for rc in rects:
      if y > rc.y and y < rc.bottom():
        ar.append(Range1D(rc.x, rc.right()))
    return Range1D.substructArrayToArray(self.getRangeAtY(y), ar)

  #(x,y)に最も近い大きさ(w,h)の空きスペースをRectangleで返す。無い場合はNone
  def findFreeSpace(self, x, y, w, h, rects):

    MAX_Y_STEP = 5.0

    #Dim ystep As Integer = Math.Truncate(h / 2 / Math.Ceiling(h / 2 / MAX_Y_STEP)) 'Ceiling=切り上げ


    ystep = int(h / 2.0 / int(h / 2.0 / MAX_Y_STEP + 0.9999))
    nElement = int(h / 2.0 / ystep) * 2 + 1 #getRangeAtYの結果を入れる配列の要素数

    #print "py ystep=" + str(ystep)
    #print "py nElement=" + str(nElement)

    if y < self.ymin + h / 2:
      y = int(self.ymin + h / 2.0 + 0.5)
    if y > self.ymax - h / 2:
      y = int(self.ymax - h / 2.0 + 0.5)

    rect = Rectangle(0, 0, 0, 0) #最も近いスペースが入る
    dist = 1000000.0 #(x,y)からrectの中心までの距離

    #yを中心として上下方向にystepずつ走査範囲を広げて wholePolygon.GetRangeAtYを実行
    ar1 = []
    for i in range(nElement):
      ar1.append([])

    for i in range((nElement - 1) / 2 + 1):
      if i == 0:
        ar1[(nElement - 1) / 2] = self.getRangeAtY(y, rects)
      else:
        ar1[(nElement - 1) / 2 - i] = self.getRangeAtY(y - i * ystep, rects)
        ar1[(nElement - 1) / 2 + i] = self.getRangeAtY(y + i * ystep, rects)

    ar2 = []
    for r in ar1:
      ar2.append(r)

    x1 = x - w / 2
    x2 = x + w / 2
    y1 = y
    y2 = y

    #まずyの高さで範囲検索

    ar = ar1[0]
    for i in range(1, nElement):
      ar = Range1D.intersectArrayToArray(ar, ar1[i])

    for r in ar:
      if r.width() >= w:
        if r.right < x2:
          rc = Rectangle(r.right - w, y1 - h / 2, w, h)
        elif r.left > x1:
          rc = Rectangle(r.left, y1 - h / 2, w, h)
        else:
          rc = Rectangle(x1, y1 - h / 2, w, h)
        d = PointXY(x, y1).distance(PointXY(rc.x + rc.w / 2, rc.y + rc.h / 2))
        if d < dist:
          rect = rc
          dist = d

    while True:
      outOfRange = 0

      #ar1,y1系はyから上方向に移動しながら範囲検索

      y1 -= ystep
      if y1 >= self.ymin + h / 2 and y - y1 < dist:

        for i in range(nElement - 1, 0, -1):
          ar1[i] = ar1[i - 1]
        ar1[0] = self.getRangeAtY(y1 - (nElement - 1) / 2 * ystep, rects)

        ar = ar1[0]
        for i in range(1, nElement):
          ar = Range1D.intersectArrayToArray(ar, ar1[i])
        
        for r in ar:
          if r.width() >= w:
            if r.right < x2:
              rc = Rectangle(r.right - w, y1 - h / 2, w, h)
            elif r.left > x1:
              rc = Rectangle(r.left, y1 - h / 2, w, h)
            else:
              rc = Rectangle(x1, y1 - h / 2, w, h)
            d = PointXY(x, y1).distance(PointXY(rc.x + rc.w / 2, rc.y + rc.h / 2))
            if d < dist:
              rect = rc
              dist = d
      else:
          outOfRange += 1

      #ar2,y2系はyから下方向に移動しながら範囲検索

      y2 += ystep
      if y2 <= self.ymax - h / 2 and y2 - y < dist:

        for i in range(nElement - 1):
          ar2[i] = ar2[i + 1]
        ar2[nElement - 1] = self.getRangeAtY(y2 + (nElement - 1) / 2 * ystep, rects)

        ar = ar2[0]
        for i in range(1, nElement):
          ar = Range1D.intersectArrayToArray(ar, ar2[i])

        for r in ar:
          if r.width() >= w:
            if r.right < x2:
              rc = Rectangle(r.right - w, y2 - h / 2, w, h)
            elif r.left > x1:
              rc = Rectangle(r.left, y2 - h / 2, w, h)
            else:
              rc = Rectangle(x1, y2 - h / 2, w, h)
            d = PointXY(x, y2).distance(PointXY(rc.x + rc.w / 2, rc.y + rc.h / 2))
            if d < dist:
              rect = rc
              dist = d
      else:
        outOfRange += 1

      if outOfRange == 2:
        break

    if dist < 1000000.0:
      return rect
    else:
      return None





#一次元の範囲を管理
class Range1D:
  left = 1
  right = 0

  def __init__(self, x1=0, x2=0):
    if x2 >= x1:
      self.left = x1
      self.right = x2
    else:
      self.left = x2
      self.right = x1

  def clone(self):
    return Range1D(self.left, self.right)

  def width(self):
    return self.right - self.left + 1

  def isEmpty(self):
    return self.width() <= 0

  #範囲から範囲を引く x1,x2はintまたはfloat
  #二つに分割された場合は片方のクラスを返す。無い場合はNoneを返す
  #この関数により範囲が消滅することもあるので、Substruct()実行後はIsEmpty()などでクラスの有効性をチェックすること
  def substruct(self, x1, x2):
    if x2 >= x1:
      l = x1
      r = x2
    else:
      l = x2
      r = x1
    if r < self.left: #左側範囲外
      return None
    if l < self.left and r >= self.left and r <= self.right: #左側一部カット(自分の長さが0になることがある)
      self.left = r + 1
      return None
    if l >= self.left and r <= self.right: #範囲内
      l_width = l - self.left
      r_width = self.right - r
      if l_width > 0:
        rr = self.right
        self.right = self.left + l_width
        if r_width > 0:
          return Range1D(rr - r_width, rr) #中央カット。右側を新しいクラスで返す
        else:
          return None #右側カット
      elif r_width > 0:
        self.left = self.right - r_width
        return None #左側カット
      else:
        self.left = 1
        self.right = 0
        return None #無くなった
    if r > self.right and l <= self.right and l >= self.left: #右側一部カット(自分の長さが0になることがある)
        self.right = l + 1
        return None
    if l > self.right: #右側範囲外
        return None
    if l < self.left and r > self.right: #範囲に覆われた
        self.left = 1
        self.right = 0
        return None #無くなった
    raise Exception("Unreachable code")


  #範囲と範囲でアンドをとる
  #r1,r2はRange1D。関数はRange1DまたはNoneを返す
  @staticmethod
  def intersect(r1, r2):
    if r2.right < r1.left: #左側範囲外(長さ0)
      return None
    if r2.left < r1.left and r2.right >= r1.left and r2.right <= r1.right: #左側一部重なり
      return Range1D(r1.left, r2.right)
    if r2.left >= r1.left and r2.right <= r1.right: #範囲内(更新)
      return Range1D(r2.left, r2.right)
    if r2.right > r1.right and r2.left <= r1.right and r2.left >= r1.left: #右側一部重なり
      return Range1D(r2.left, r1.right)
    if r2.left > r1.right: #右側範囲外(長さ0)
      return None
    if r2.left < r1.left and r2.right > r1.right: #範囲に覆われた(更新不要)
      return Range1D(r1.left, r1.right)
    raise Exception("Unreachable code")

  #r1-r2の残った範囲を計算
  #r1,r2はRange1D配列。関数もRange1D配列を返すが、空の場合がある
  @staticmethod
  def substructArrayToArray(r1, r2):
    ar = []
    for r in r1:
      ar.append(r.clone())
    i = 0
    while i < len(ar):
      remove = False
      for r in r2:
        rr = ar[i].substruct(r.left, r.right)
        if rr != None:
          ar.append(rr)
        if ar[i].isEmpty():
          remove = True
          break
      if remove == True:
        ar.pop(i)
      else:
        i += 1
    return ar

  #r1 AND r2 を計算
  #r1,r2はRange1D配列。関数もRange1D配列を返すが、空の場合がある
  @staticmethod
  def intersectArrayToArray(r1, r2):
    ar = []
    for a in r1:
      for b in r2:
        r = Range1D.intersect(a, b)
        if r != None:
          ar.append(r)
    return ar

  def toString(self):
    if self.isEmpty():
      return "(Empty)"
    else:
      return "(" + str(self.left) + " to " + str(self.right) + ")"




class PointXY:
  x = 0.0
  y = 0.0

  def __init__(self, x=0.0, y=0.0):
    self.x = x
    self.y = y

  def __add__(self, other):
    if isinstance(other, PointXY):
      return PointXY(self.x + other.x, self.y + other.y)
    else:
      raise ValueError("Param type error")

  def __sub__(self, other):
    if isinstance(other, PointXY):
      return PointXY(self.x - other.x, self.y - other.y)
    else:
      raise ValueError("Param type error")

  def __mul__(self, other):
    t = type(other)
    if t == "int" or t == "float":
      return PointXY(self.x * other, self.y * other)
    else:
      raise ValueError("Param type error")

  def clone(self):
    return PointXY(self.x, self.y)

  def distance(self, p):
    if isinstance(p, PointXY):
      return math.sqrt((self.x - p.x) * (self.x - p.x) + (self.y - p.y) * (self.y - p.y))
    else:
      raise ValueError("Param type error")

  def rotate(self, ang, clockwise=True):
    theta = ang * math.pi / 180.0
    if clockwise == False:
      theta = -theta
    sin_t = math.sin(theta)
    cos_t = math.cos(theta)
    return PointXY(cos_t * self.x - sin_t * self.y, sin_t * self.x + cos_t * self.y)

  def toString(self):
    return "(" + str(self.x) + "," + str(self.y) + ")"


class Rectangle:
  x = 0
  y = 0
  w = 0
  h = 0

  def __init__(self, x=0, y=0, w=0, h=0):
    self.x = int(x + 0.5)
    self.y = int(y + 0.5)
    self.w = int(w + 0.5)
    self.h = int(h + 0.5)

  def left(self):
    return self.x

  def right(self):
    return self.x + self.w

  def top(self):
    return self.y

  def bottom(self):
    return self.y + self.h

  def toString(self):
    return "(" + str(self.x) + "," + str(self.y) + "," + str(self.w) + "," + str(self.h) + ")"
