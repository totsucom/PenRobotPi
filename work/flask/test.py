# -*- coding: utf-8 -*-

import VectorFontLoader

#init (load index data from a.dict2)
vf = VectorFontLoader.VectorFontLoader("a.dict2", "a.vect2")



text = "HELLO"

#open a.vect2 file and read vectors
va = vf.getVectorArrayFromText(text)

#multiply 100 (font standard height is 1.0)
va.scale(100,100)

#M = MoveTo : start of writing point 
#L = LineTo : line to current point to new point
#D = Dummy  : Nothing to write (for space" " etc.)
for vu in va.ar:
  print vu.toCommand()
