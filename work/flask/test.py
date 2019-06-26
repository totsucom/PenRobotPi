# -*- coding: utf-8 -*-

import struct

dictPath = "font.dict"
vectPath = "font.vector"
indexData = bytes(0)

with open(dictPath, "rb") as f:
  indexData = f.read((65536 - 42269) * 3)

def getVectorArray(loc):
  with open(vectPath, "rb") as f:
    f.seek(loc)
    buf = f.read(2)
    up = struct.unpack_from("<H", buf)
    list = []
    n = up[0]
    while n > 0:
      buf = f.read(9)
      up = struct.unpack_from("<cff", buf)
      list.append(up[0] + "{:.2f}".format(up[1]) + "," + "{:.2f}".format(up[2]))
      n -= 1
  return list

def utf16ToLocation(utf16):
  if utf16 in {0, 0x3D5}:
    i = utf16
  elif utf16 in {0x3D6, 0x2103}:
    return -2
  elif utf16 in range(0x2104, 0x22C2):
    i = utf16 - 7470
  elif utf16 in {0x22C3, 0x2E8B}:
    return -3
  elif utf16 in range(0x2E8C, 0x30FC):
    i = utf16 - 7470 - 3017
  elif utf16 in {0x30FD, 0x471E}:
    return -4
  elif utf16 == 0x471F:
    i = utf16 - 7470 - 3017 - 5666
  elif utf16 in {0x4720, 0x4DFF}:
    return -5
  elif utf16 in {0x4E00, 0x9FA0}:
    i = utf16 - 7470 - 3017 - 5666 - 1760
  elif utf16 in {0x9FA1, 0xFA10}:
    return -6
  elif utf16 in {0xFA11, 0xFA66}:
    i = utf16 - 7470 - 3017 - 5666 - 1760 - 23152
  elif utf16 in {0xFA67, 0xFF20}:
    return -7
  elif utf16 in {0xFF21, 0xFFFF}:
    i = utf16 - 7470 - 3017 - 5666 - 1760 - 23152 - 1210
  else:
    return -8
  i *= 3
  loc = ord(indexData[i]) + (ord(indexData[i + 1]) << 8) + (ord(indexData[i + 2]) << 16)
  if loc == 0xFFFFFF:
    return -9
  else:
    return loc


str = u"あ"
loc = utf16ToLocation(ord(str))
if loc >= 0:
  print getVectorArray(loc)

