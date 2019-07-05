# -*- coding: utf-8 -*-

import struct

class VectorFontLoader:
  dictPath = ""
  vectPath = ""
  indexData = ""
  acceptableRange = []

  #constructor
  #download whole .dict file on memory
  def __init__(self, dict_path, font_path):
    self.dictPath = dict_path
    self.vectPath = font_path

    with open(self.dictPath, "rb") as f:

      #n = number of valid utf16 code ranges
      n = struct.unpack_from("<H", f.read(2))
      unregisteredCount = 0
      utf16 = 0
      for i in range(n[0]):
        #valid utf16 range r[0] to r[1]
        r = struct.unpack_from("<HH", f.read(4))
        self.acceptableRange.append(r)
        #count invalid utf16 codes
        unregisteredCount += r[0] - utf16
        utf16 = r[1] + 1
      unregisteredCount += 65536 - utf16

      #read index data. it is 3bytes
      self.indexData = f.read((65536 - unregisteredCount) * 3)

  #get font vectors from .vect file
  #1. get location from indexData(.dict file)
  #2. open .vect file and "seek" to location
  #3. read vector data
  def getVectorArray(self, utf16):
    va = VectorArray()

    loc = self.__utf16ToLocation(utf16)
    if loc < 0:
      print "VectorFont location error " + str(loc)
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
    margin = 0.08 #margin between chars
    x = 0
    ar = VectorArray()
    with open(self.vectPath, "rb") as f:
      for c in text:
        utf16 = ord(c)
        loc = self.__utf16ToLocation(utf16)
        if loc >= 0:
          f.seek(loc)
          buf = f.read(2)
          up = struct.unpack_from("<H", buf)
          vector_count = up[0]
          va = VectorArray()
          while vector_count > 0:
            buf = f.read(9)
            up = struct.unpack_from("<cff", buf)
            va.add(VectorUnit(up[0], up[1], up[2]))
            vector_count -= 1
          width = va.getBound()[2]
          va.offset(x, 0)
          for vu in va.ar:
            ar.add(vu)
          x += width
          x += margin
    return ar

  def __utf16ToLocation(self, utf16):
    offset = 0
    for r in self.acceptableRange:
      if utf16 < r[0]:
        return -1
      if utf16 <= r[1]:
        i = ((utf16 - r[0]) + offset) * 3;
        return ord(self.indexData[i]) \
              + (ord(self.indexData[i + 1]) << 8) \
              + (ord(self.indexData[i + 2]) << 16)
      offset += r[1] - r[0] + 1
    return -1

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
  cmd = ' ' # 'D':NONE(DUMMY) 'M':MOVETO 'L':LINETO
  x = 0.0
  y = 0.0

  def __init__(self, cmd, x, y):
    if not cmd in ["L","M","D"]:
      print "VectorUnit() unknown command"
      cmd = "D"
    self.cmd = cmd
    self.x = float(x)
    self.y = float(y)

  def toCommand(self):
    return self.cmd + "{:.2f}".format(self.x) + "," + "{:.2f}".format(self.y)

