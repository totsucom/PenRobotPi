# -*- coding: utf-8 -*-

import struct

class VectorFontLoader:
  dictPath = ""
  vectPath = ""
  indexData = bytes(0)

  def __init__(self, dict_path, font_path):
    self.dictPath = dict_path
    self.vectPath = font_path

    with open(self.dictPath, "rb") as f:
      self.indexData = f.read((65536 - 42269) * 3)

  def getVectorArray(self, utf16):
    va = VectorArray()
    loc = self.__utf16ToLocation(utf16)
    if loc < 0:
      print "location error " + str(loc)
      return va

    with open(self.vectPath, "rb") as f:
      f.seek(loc)
      buf = f.read(2)
      up = struct.unpack_from("<H", buf)

      n = up[0]
      while n > 0:
        buf = f.read(9)
        up = struct.unpack_from("<cff", buf)
        va.add(VectorUnit(up[0], up[1], up[2]))
        n -= 1
    return va

  def getVectorArrayFromText(self, text):
    x = 0
    ar = VectorArray()
    with open(self.vectPath, "rb") as f:
      for c in text:
        loc = self.__utf16ToLocation(ord(c))
        if loc >= 0:
          f.seek(loc)
          buf = f.read(2)
          up = struct.unpack_from("<H", buf)
          n = up[0]
          va = VectorArray()
          while n > 0:
            buf = f.read(9)
            up = struct.unpack_from("<cff", buf)
            va.add(VectorUnit(up[0], up[1], up[2]))
            n -= 1
          w = va.getSize()[1]
          va.offset(x, 0)
          for vu in va.ar:
            ar.add(vu)
          x += w
    #余白を除く
    bound = ar.getBound()
    xmin = bound[0]
    ymin = bound[1]
    xmax = bound[2]
    ymax = bound[3]
    if xmin != 0 or ymin != 0:
      ar.offset(-xmin, -ymin)
    return ar, xmax-xmin, ymax-ymin

  def __utf16ToLocation(self, utf16):
    if utf16 in range(0, 0x3D5):
      i = utf16
    elif utf16 in range(0x3D6, 0x2103):
      return -2
    elif utf16 in range(0x2104, 0x22C2):
      i = utf16 - 7470
    elif utf16 in range(0x22C3, 0x2E8B):
      return -3
    elif utf16 in range(0x2E8C, 0x30FC):
      i = utf16 - 7470 - 3017
    elif utf16 in range(0x30FD, 0x471E):
      return -4
    elif utf16 == 0x471F:
      i = utf16 - 7470 - 3017 - 5666
    elif utf16 in range(0x4720, 0x4DFF):
      return -5
    elif utf16 in range(0x4E00, 0x9FA0):
      i = utf16 - 7470 - 3017 - 5666 - 1760
    elif utf16 in range(0x9FA1, 0xFA10):
      return -6
    elif utf16 in range(0xFA11, 0xFA66):
      i = utf16 - 7470 - 3017 - 5666 - 1760 - 23152
    elif utf16 in range(0xFA67, 0xFF20):
      return -7
    elif utf16 in range(0xFF21, 0xFFFF):
      i = utf16 - 7470 - 3017 - 5666 - 1760 - 23152 - 1210
    else:
      return -8
    i *= 3
    loc = ord(self.indexData[i]) + (ord(self.indexData[i + 1]) << 8) + (ord(self.indexData[i + 2]) << 16)
    if loc == 0xFFFFFF:
      return -9
    else:
      return loc

class VectorArray:
  ar = []

  def __init__(self):
    self.ar = []

  def count(self):
    return len(self.ar)

  def add(self, vecunit):
    self.ar.append(vecunit)

  def offset(self, x, y):
    for vu in self.ar:
      vu.x += x
      vu.y += y

  def scale(self, x, y):
    for vu in self.ar:
      vu.x *= x
      vu.y *= y

  #文字サイズを返す(1文字のときだけ有効)
  def getSize(self):
    found = False
    xmin = 0
    xmax = 0
    ymin = 0
    ymax = 0
    for vu in self.ar:
      if found == True:
        if vu.x < xmin:
          xmin = vu.x
        if vu.x > xmax:
          xmax = vu.x
        if vu.y < ymin:
          ymin = vu.y
        if vu.y > ymax:
          ymax = vu.y
      else:
        xmin = vu.x
        xmax = vu.x
        ymin = vu.y
        ymax = vu.y
        found = True
    if found == False:
      return 0, 0
    else:
      return xmax+xmin, 120

  #全ベクトルの範囲を返す
  def getBound(self):
    found = False
    xmin = 0
    xmax = 0
    ymin = 0
    ymax = 0
    for vu in self.ar:
      if found == True:
        if vu.x < xmin:
          xmin = vu.x
        if vu.x > xmax:
          xmax = vu.x
        if vu.y < ymin:
          ymin = vu.y
        if vu.y > ymax:
          ymax = vu.y
      else:
        xmin = vu.x
        xmax = vu.x
        ymin = vu.y
        ymax = vu.y
        found = True
    if found == False:
      return 0, 0, 0, 0
    else:
      return xmin, ymin, xmax, ymax

class VectorUnit:
  cmd = 'M'
  x = 0.0
  y = 0.0

  def __init__(self, cmd, x, y):
    self.cmd = cmd
    self.x = float(x)
    self.y = float(y)

  def toCommand(self):
    return self.cmd + "{:.2f}".format(self.x) + "," + "{:.2f}".format(self.y)

