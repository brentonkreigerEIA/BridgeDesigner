import pandas as pd
import shutil as shit
import numpy as np

# Update "learning" variables as "weights" - not physical

# First, start with a range.
wm = 1  #weight of masonry
we = 1  #weight of excavation
wc = 1  #weight of cement
ws = 1  #weight of sand
wg = 1  #weight of gravel
wr = 1  #weight of rocks

# Open and run BridgeDesigner
stream = open("BridgeDesigner_Learning.py")
read_file = stream.read()
exec(read_file)