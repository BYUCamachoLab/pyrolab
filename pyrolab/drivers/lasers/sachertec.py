import os

os.environ['PATH'] = ("C:\\Program Files\\SacherLasertechnik\\MotorMotion 2.1\\data"
+ ";" + os.environ['PATH'])

from ctypes import *

from sacher_tec import epos_motor as epm
from sacher_tec._utils import c_dword, c_word

name = create_string_buffer(("EPOS2").encode('utf-8'))
protocol = create_string_buffer(("MAXON SERIAL V2").encode('utf-8'))
interface = create_string_buffer(("USB").encode('utf-8'))
port = create_string_buffer(("USB0").encode('utf-8'))
name_size = c_word(10)
baudrate = c_dword(0)
timeout = c_dword(0)
node_id = c_word(0)
dialog = c_int(3)
error = c_dword(0)

out = epm.VCS_OpenDeviceDlg(byref(error))

print(out)
print(error)

handle = epm.VCS_OpenDevice(name,protocol,interface,port,byref(error))
print(handle)
print(error)

out = epm.VCS_SetProtocolStackSettings(handle,baudrate,timeout,byref(error))
print(out)
print(error)

out = epm.VCS_FindDeviceCommunicationSettings(byref(handle),byref(name),byref(protocol),byref(interface),byref(port),name_size,byref(baudrate),byref(timeout),byref(node_id),dialog,byref(error))
                                            # [c_int, c_char_p, c_char_p, c_char_p, c_char_p, c_word, POINTER(c_dword), POINTER(c_dword), POINTER(c_word), POINTER(c_int), POINTER(c_dword)], c_bool)
print(out)
print(error)
print(node_id)

out = epm.VCS_CloseAllDevices(byref(error))

print(out)
print(error)