from distutils.core import setup
import Arduino
import py2exe
import sys,os

#sys.argv.append('py2exe')

#icon = os.path.join(os.path.dirname(sys.executable),'DLLs\py.ico')
setup(
      options = {'py2exe': {
                            'optimize' : 2,
                            'dist_dir' : 'LaserControl',
                            'includes' : ['sip', 'Arduino'],
                            'bundle_files':1 # compress all files into 1 file
                            }},
      name = 'Laser Control- AOTF',
      zipfile = 'None',
      windows = [
                 {
                  'script': "Main.py",
                  #'icon_resources':[(1,''py.ico'')],
                  },
                 ],
      description = "Control AOTF Flexibly",
      version = "0.1",
      author = "Bei Liu",
      
      )