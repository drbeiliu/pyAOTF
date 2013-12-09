
import re
from serial.tools import list_ports
from wingetport import portiter, full_port_name
import time

for item in list_ports.comports():
	print item[1]
	if re.search('USB', item[1]) is not None :
		selCOM = item[0]
		print selCOM
print tuple(portiter())
#full_port_name(1)
#print time.ctime()
a = "%s"%time.strftime('%X')
if isinstance(a, str):
	print 'hi'
