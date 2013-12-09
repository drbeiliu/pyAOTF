import serial.tools.list_ports

for i,j,k in serial.tools.list_ports.comports():
	print i
	print j
	print k
print j.split('(')[0]