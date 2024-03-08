"""Version: 1.24744.20240303
Win32:
    (a) x86: XP SP3 or above; CPU supports SSE2 instruction set or above
    (b) x64: Win7 or above
"""
import sys, ctypes, os.path

"""
**********************************************************************
*                             C API                                  *
* Uvcsam_enum (optional)                                             *
* ----> Uvcsam_open                                                  *
* ----> enum resolutions, set resolution, set exposure time, etc     *
* ----> Uvcsam_start                                                 *
* ----> callback for image and events                                *
* ----> Uvcsam_close                                                 *
**********************************************************************
"""
UVCSAM_MAX              = 16

UVCSAM_FWVERSION        = 0x00000001    # firmware version, such as: 1.2.3
UVCSAM_FWDATE           = 0x00000002    # firmware date, such as: 20191018
UVCSAM_HWVERSION        = 0x00000003    # hardware version, such as: 1.2
UVCSAM_REVISION         = 0x00000004    # revision
UVCSAM_GAIN             = 0x00000005    # gain, percent, 100 means 100%
UVCSAM_EXPOTIME         = 0x00000006    # exposure time, in microseconds
UVCSAM_AE_ONOFF         = 0x00000007    # auto exposure: 0 = off, 1 = on
UVCSAM_AE_TARGET        = 0x00000008    # auto exposure target, range = [UVCSAM_AE_TARGET_MIN, UVCSAM_AE_TARGET_MAX]
UVCSAM_AE_ROILEFT       = 0x00000009    # auto exposure roi: left
UVCSAM_AE_ROITOP        = 0x0000000a    # top
UVCSAM_AE_ROIRIGHT      = 0x0000000b    # right
UVCSAM_AE_ROIBOTTOM     = 0x0000000c    # bottom
UVCSAM_AWB              = 0x0000000d    # white balance: 0 = manual, 1 = global auto, 2 = roi, 3 = roi mode 'once'
UVCSAM_AWB_ROILEFT      = 0x0000000e    # white balance roi: left
UVCSAM_AWB_ROITOP       = 0x0000000f    # top
UVCSAM_AWB_ROIRIGHT     = 0x00000010    # right
UVCSAM_AWB_ROIBOTTOM    = 0x00000011    # bottom
UVCSAM_WBGAIN_RED       = 0x00000012    # white balance gain, range: [UVCSAM_WBGAIN_MIN, UVCSAM_WBGAIN_MAX]
UVCSAM_WBGAIN_GREEN     = 0x00000013
UVCSAM_WBGAIN_BLUE      = 0x00000014
UVCSAM_VFLIP            = 0x00000015    # flip vertical
UVCSAM_HFLIP            = 0x00000016    # flip horizontal
UVCSAM_FFC              = 0x00000017    # flat field correction
                                        #     put:
                                        #         0: disable
                                        #         1: enable
                                        #         -1: reset
                                        #         (0xff000000 | n): set the average number to n, [1~255]
                                        #     get:
                                        #         (val & 0xff): 0 -> disable, 1 -> enable, 2 -> inited
                                        #         ((val & 0xff00) >> 8): sequence
                                        #         ((val & 0xff0000) >> 8): average number
                                        #
UVCSAM_FFC_ONCE         = 0x00000018    # ffc (flat field correction) 'once'
UVCSAM_LEVELRANGE_AUTO  = 0x00000019    # level range auto
UVCSAM_LEVELRANGE_LOW   = 0x0000001a    # level range low
UVCSAM_LEVELRANGE_HIGH  = 0x0000001b    # level range high
UVCSAM_HISTOGRAM        = 0x0000001c    # histogram
UVCSAM_CHROME           = 0x0000001d    # monochromatic mode
UVCSAM_NEGATIVE         = 0x0000001e    # negative film
UVCSAM_PAUSE            = 0x0000001f    # pause
UVCSAM_SHARPNESS        = 0x00000020
UVCSAM_SATURATION       = 0x00000021
UVCSAM_GAMMA            = 0x00000022
UVCSAM_CONTRAST         = 0x00000023
UVCSAM_BRIGHTNESS       = 0x00000024
UVCSAM_HZ               = 0x00000025    # 2 -> 60HZ AC;  1 -> 50Hz AC;  0 -> DC
UVCSAM_HUE              = 0x00000026
UVCSAM_LIGHT_SOURCE     = 0x00000027    # light source: 0~8
UVCSAM_REALTIME         = 0x00000028    # realtime: 1 => ON, 0 => OFF
UVCSAM_FORMAT           = 0x000000fe    # output format: 0 => BGR888, 1 => BGRA8888, 2 => RGB888, 3 => RGBA8888; default: 0
                                        # MUST be set before start
                                        #
UVCSAM_MAGIC            = 0x000000ff

UVCSAM_GPIO             = 0x08000000    # GPIO: 0~7 bit corresponds to GPIO
UVCSAM_RES              = 0x10000000    # resolution:
                                        #    Can be changed only when camera is not running.
                                        #    To get the number of the supported resolution, use: Uvcsam_range(h, UVCSAM_RES, nullptr, &num, nullptr)
                                        #
UVCSAM_CODEC            = 0x20000000    # 0: mjpeg, 1: YUY2; Can be changed only when camera is not running
UVCSAM_WIDTH            = 0x40000000    # to get the nth width, use: Uvcsam_get(h, UVCSAM_WIDTH | n, &width)
UVCSAM_HEIGHT           = 0x80000000

"""
********************************************************************
* How to enum the resolutions:                                     *
*     res = cam_.range(UVCSAM_RES)                                 *
*     for i in range(0, res[0] + 1):                               *
*         width = cam_.get(UVCSAM_WIDTH | i)                       *
*         height = cam_.get(UVCSAM_HEIGHT | i)                     *
*         print('{}: {} x {}\n'.format(i, width, height))          *
********************************************************************

********************************************************************
* "Direct Mode" vs "Pull Mode"                                     *
* (1) Direct Mode:                                                 *
*     (a) cam_.start(h, pFrameBuffer, ...)                         *
*     (b) pros: simple, slightly more efficient                    *
* (2) Pull Mode:                                                   *
*     (a) cam_.start(h, None, ...)                                 *
*     (b) use cam_.pull(h, pFrameBuffer) to pull image             *
*     (c) pros: never frame confusion                              *
********************************************************************
"""

# event
UVCSAM_EVENT_AWB        = 0x0001
UVCSAM_EVENT_FFC        = 0x0002
UVCSAM_EVENT_LEVELRANGE = 0x0004
UVCSAM_EVENT_IMAGE      = 0x0008
UVCSAM_EVENT_TRIGGER    = 0x0010    # user push the trigger button
UVCSAM_EVENT_FLIP       = 0x0020    # user push the flip button
UVCSAM_EVENT_EXPOTIME   = 0x0040    # auto exposure: exposure time changed
UVCSAM_EVENT_GAIN       = 0x0080    # auto exposure: gain changed
UVCSAM_EVENT_DISCONNECT = 0x0100    # camera disconnect
UVCSAM_EVENT_ERROR      = 0x0200    # error

UVCSAM_ROI_WIDTH_MIN    = 32
UVCSAM_ROI_HEIGHT_MIN   = 32

UVCSAM_AE_TARGET_MIN    = 16        # auto exposure target: minimum
UVCSAM_AE_TARGET_DEF    = 48        # auto exposure target: default
UVCSAM_AE_TARGET_MAX    = 208       # auto exposure target: maximum

UVCSAM_WBGAIN_MIN       = 1
UVCSAM_WBGAIN_MAX       = 255
UVCSAM_WBGAIN_RED_DEF   = 128
UVCSAM_WBGAIN_GREEN_DEF = 64
UVCSAM_WBGAIN_BLUE_DEF  = 128

UVCSAM_LEVELRANGE_MIN   = 0
UVCSAM_LEVELRANGE_MAX   = 255

UVCSAM_LIGHT_SOURCE_MIN = 0
UVCSAM_LIGHT_SOURCE_MAX = 8
UVCSAM_LIGHT_SOURCE_DEF = 5

def TDIBWIDTHBYTES(bits):
    return ((bits + 31) // 32 * 4)

class UvcsamDevice:
    def __init__(self, displayname, id):
        self.displayname = displayname   # display name
        self.id = id                     # unique and opaque id of a connected camera, for Uvcsam_open

class HRESULTException(OSError):
    def __init__(self, hr):
        OSError.__init__(self, None, ctypes.FormatError(hr).strip(), None, hr)
        self.hr = hr

class _Device(ctypes.Structure):
    _fields_ = [('displayname', ctypes.c_wchar * 128), # display name
                ('id', ctypes.c_wchar * 128)]          # unique and opaque id of a connected camera, for Uvcsam_open

class Uvcsam:
    __CALLBACK = ctypes.WINFUNCTYPE(None, ctypes.c_uint, ctypes.py_object)
    __lib = None

    @staticmethod
    def __errcheck(result, fun, args):
        if result < 0:
            raise HRESULTException(result)
        return args

    @staticmethod
    def __convertStr(x):
        if isinstance(x, str):
            return x
        else:
            return x.decode('ascii')

    @classmethod
    def Version(cls):
        """get the version of this dll, which is: 1.24744.20240303"""
        cls.__initlib()
        return cls.__lib.Uvcsam_version()

    @staticmethod
    def __convertDevice(a):
        return UvcsamDevice(__class__.__convertStr(a.displayname), __class__.__convertStr(a.id))

    @classmethod
    def enum(cls):
        """enumerate the cameras that are currently connected to computer"""
        cls.__initlib()
        a = (_Device * UVCSAM_MAX)()
        n = cls.__lib.Uvcsam_enum(a)
        arr = []
        for i in range(0, n):
            arr.append(cls.__convertDevice(a[i]))
        return arr

    def __init__(self, h):
        """the object of Uvcsam must be obtained by classmethod Open, it cannot be obtained by obj = uvcsam.Uvcsam()"""
        self.__h = h
        self.__fun = None
        self.__ctx = None
        self.__cb = None

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __nonzero__(self):
        return self.__h is not None

    def __bool__(self):
        return self.__h is not None

    @classmethod
    def open(cls, camId):
        """the object of Uvcsam must be obtained by classmethod Open, it cannot be obtained by obj = uvcsam.Uvcsam()"""
        cls.__initlib()
        h = cls.__lib.Uvcsam_open(camId)
        if h is None:
            return None
        return __class__(h)

    def close(self):
        if self.__h:
            self.__lib.Uvcsam_close(self.__h)
            self.__h = None

    @staticmethod
    def __tcallbackFun(nEvent, ctx):
        if ctx:
            ctx.__callbackFun(nEvent)

    def __callbackFun(self, nEvent):
        if self.__fun:
            self.__fun(nEvent, self.__ctx)

    def start(self, buf, fun, ctx):
        self.__fun = fun
        self.__ctx = ctx
        self.__cb = __class__.__CALLBACK(__class__.__tcallbackFun)
        self.__lib.Uvcsam_start(self.__h, buf, self.__cb, ctypes.py_object(self))

    def stop(self):
        self.__lib.Uvcsam_stop(self.__h)

    def pull(self, buf):
        self.__lib.Uvcsam_pull(self.__h, buf)

    def record(self, filePath):
        """
        (filePath == None) means to stop record.
        support file extension: *.asf, *.mp4, *.mkv
        """
        self.__lib.Uvcsam_record(self.__h, filePath)

    def put(self, nId, val):
        """nId: UVCSAM_XXXX"""
        self.__lib.Uvcsam_put(self.__h, ctypes.c_uint(nId), ctypes.c_int(val))

    def get(self, nId):
        x = ctypes.c_int(0)
        self.__lib.Uvcsam_get(self.__h, ctypes.c_uint(nId), ctypes.byref(x))
        return x.value

    def range(self, nId):
        nMin = ctypes.c_int(0)
        nMax = ctypes.c_int(0)
        nDef = ctypes.c_int(0)
        self.__lib.Uvcsam_range(self.__h, ctypes.c_uint(nId), ctypes.byref(nMin), ctypes.byref(nMax), ctypes.byref(nDef))
        return (nMin.value, nMax.value, nDef.value)

    @classmethod
    def __initlib(cls):
        if cls.__lib is None:
            try: # Firstly try to load the library in the directory where this file is located
                dir = os.path.dirname(os.path.realpath(__file__))
                cls.__lib = ctypes.windll.LoadLibrary(os.path.join(dir, 'uvcsam.dll'))
            except OSError:
                pass

            if cls.__lib is None:
                cls.__lib = ctypes.windll.LoadLibrary('uvcsam.dll')

            cls.__lib.Uvcsam_version.restype = ctypes.c_wchar_p
            cls.__lib.Uvcsam_version.argtypes = None
            cls.__lib.Uvcsam_enum.restype = ctypes.c_uint
            cls.__lib.Uvcsam_enum.argtypes = [_Device * UVCSAM_MAX]
            cls.__lib.Uvcsam_open.restype = ctypes.c_void_p
            cls.__lib.Uvcsam_open.argtypes = [ctypes.c_wchar_p]
            cls.__lib.Uvcsam_start.restype = ctypes.c_int
            cls.__lib.Uvcsam_start.argtypes = [ctypes.c_void_p, ctypes.c_char_p, cls.__CALLBACK, ctypes.py_object]
            cls.__lib.Uvcsam_start.errcheck = cls.__errcheck
            cls.__lib.Uvcsam_stop.restype = ctypes.c_int
            cls.__lib.Uvcsam_stop.argtypes = [ctypes.c_void_p]
            cls.__lib.Uvcsam_stop.errcheck = cls.__errcheck
            cls.__lib.Uvcsam_close.restype = None
            cls.__lib.Uvcsam_close.argtypes = [ctypes.c_void_p]
            cls.__lib.Uvcsam_put.restype = ctypes.c_int
            cls.__lib.Uvcsam_put.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int]
            cls.__lib.Uvcsam_put.errcheck = cls.__errcheck
            cls.__lib.Uvcsam_get.restype = ctypes.c_int
            cls.__lib.Uvcsam_get.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_int)]
            cls.__lib.Uvcsam_get.errcheck = cls.__errcheck
            cls.__lib.Uvcsam_range.restype = ctypes.c_int
            cls.__lib.Uvcsam_range.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
            cls.__lib.Uvcsam_range.errcheck = cls.__errcheck
            cls.__lib.Uvcsam_pull.restype = ctypes.c_int
            cls.__lib.Uvcsam_pull.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            cls.__lib.Uvcsam_pull.errcheck = cls.__errcheck
            cls.__lib.Uvcsam_record.restype = ctypes.c_int
            cls.__lib.Uvcsam_record.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            cls.__lib.Uvcsam_record.errcheck = cls.__errcheck