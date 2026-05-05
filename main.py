""" IMPORT SESSION AND PIN DEFINITIONS """
import time
import sys
from machine import Timer, Pin, ADC
import neopixel
from machine import UART


ELM_ENA = Pin(14, Pin.OUT, False)		# ELM327 board ENABLE PIN definition (Operate relay)
pot = ADC(Pin(28))

############################
#	VARIABLE DEFINITIONS
############################
kmh = "kmh"
rpm = "rpm"
vb = "Vb="
OK = "OK"
brkt = "I    I"
clrRPM = "    "
ERROR = "ERROR! :("
ComErrCntr = 0
flgInitReady = 0
secCount = 0
annuFlg = False
DispBrightness = 1
DispBrightness_old = 1
speedRaw = 0
rpmRaw = 0
voltageRaw = 0
rqstPoll = False
tickCount = 0

initStr_0 = "STARTING"
initStr_1 = "DISPLAY INIT        "
initStr_2 = "OBD BOARD PWR ON    "
initStr_3 = "OBD BOARD INIT      "
initStr_4 = "INIT VEHICLE COM    "
initStr_5 = "START MAIN SCREEN   "
ErrStr_0 =  "COM ERROR->OBD BRD!"
ErrStr_1 =  "COM ERROR->VEHICLE!"
loading =   "LOADING..."

############################
#	SERIAL PORT DECLARATIONS
############################
VFD = UART(0)
VFD.init(9600, bits=8, parity=None, stop=1, tx=Pin(0, pull=Pin.PULL_UP), invert=1, flow=0)

OBD = UART(1)
OBD.init(9600, bits=8, parity=None, stop=1, tx=Pin(4), rx=Pin(5), invert=0, flow=0, timeout=120) #UART.INV_RX 150

def SendOverSerial(device, msg, payload):
    dOut = None
    if device == "DISP":
        if msg == "cmd":
            dOut = bytes(payload)
            #print("\tSERIAL out cmd -> VFD: " + str(dOut))
            VFD.write(dOut)
        elif msg == "text":
            dOut = payload.encode("ascii")
            #print("\tSERIAL out text -> VFD:" + str(dOut))
            VFD.write(dOut)
    elif device == "ELM":
        if msg == "PID":
            dOut = bytes(payload)
            #print("\tSERIAL out PID -> OBD: " + str(dOut))
            OBD.write(dOut)               
        elif msg == "AT":
            dOut = payload.encode()
            #print("\tSERIAL out AT cmd-> OBD: " + str(dOut))
            OBD.write(dOut)

##########################
#	GPIO RELATED FUNCTIONS
##########################
def ElmEna(state):
    if state == "ON":
        ELM_ENA.on()
        print("ELM327 module is enabled...")
    elif state == "OFF":
        ELM_ENA.off()
        print("ELM327 module is disabled...")

############################
#	VFD FUNCTION DEFINITIONS
############################
def ClrScrn():
    """
    Clears the screen.
    parameters:
        None.
    """
    inst = [0x0C]
    #print('\n')
    print("Cleraing screen...")
    SendOverSerial("DISP","cmd", inst)
    
def DispInit():
    """
    Initializes display. Reset display to their initial values. Screen cleared, curso is at home position.
    parameters:
        None.
    """
    inst = [0x1B, 0x40]
    #print('\n')
    print("Initialize dsiplay...")
    SendOverSerial("DISP", "cmd", inst)
    
def ClrCrsrLine(line):
    """
    Clears the cursor line.
    parameters:
        line = line to clear. Coud be 1 or 2.
    """
    inst = [0x24]
    CrsrSetToPos(1,line)
    #print('\n')
    print("Clearing line " + str(line))
    SendOverSerial("DISP", "cmd", inst)
    
def CrsrOnOff(val):
    """
    Enables or disables the cursor on the screen.
    parameters:
        val = 1: cursor on, 0: cursor off
    """
    #print('\n')
    if val == 1:
        inst = [0x1F, 0x43, 0x01]
        print("Turning cursor ON...")
        SendOverSerial("DISP", "cmd", inst)

    elif val == 0:
        inst = [0x1F, 0x43, 0x00]
        print("Turning cursor OFF...")
        SendOverSerial("DISP", "cmd", inst)
        
def CrsrSetToPos(x,y):
    """
    Set the cursor to specified position. Previous displyes text will be cleared!!!
    parameters:
        x = position in the line. Could be 1 to 20.
        y = number of line. Could be 1 or 2.
    """
    inst = [0x1F, 0x24, x, y]
    #print('\n')
    #print("Setting cursor to position: " + str(x) + " line: " + str(y))
    SendOverSerial("DISP", "cmd", inst)
      
def SetBrigntness(val):
    """
    Set the brightness of the display
    parameters:
        val = level. Possible values: 1, 2, 3, 4. Additional infor: 3->70%, 4->100%
    """
    inst = [0x1F, 0x58, val]
    #print('\n')
    print("Brightness is set to " + str(val))
    SendOverSerial("DISP", "cmd", inst)
      
def SetBlinkDisplay(val):
    """
    Blinks the text on the display.
    parameters:
        val: blinking interval. Possible values 0-255. Formula: val*50ms ON, then val*50ms OFF.
        val=255->~ 13s ON/OFF, val=20->~1s ON/OFF
    """
    inst = [0x1F, 0x45, val]
    #print('\n')
    print("Display blinking set to: " + str(val))
    SendOverSerial("DISP", "cmd", inst)

def VerticalScrollMode():
    """
    Enables vertical scroll mode.
    parameters:
        None
    """
    inst = [0x1F, 0x02]
    #print('\n')
    print("Vertical scroll mode ENABLED.")
    SendOverSerial("DISP", "cmd", inst)
    
def AnnunciatorOnOff(col, state):
    """
    Turns ON or OFF the annunciator sign at the selected coloumn.
    parameters:
        col:
        state: 
    """
    if (state == "ON"):
        inst = [0x1F, 0x23, 0x01, col]
        #print('\n')
        #print("Turning annunciator ON in column " + str(col))
        SendOverSerial("DISP", "cmd", inst)
        
    elif (state == "OFF"):
        inst = [0x1F, 0x23, 0x00, col]
        #print('\n')
        #print("Turning annunciator OFF in column " + str(col))
        SendOverSerial("DISP", "cmd", inst)
    
def DefineChars(chrset):
    """
    This function defines special glyphs that will build up 2x2 position numbers and downloads it to the display as special, user defined characters.
    parameters:
        chrset = "ProcessBar": Defines the glyphs for the procesbar
        chrset = "BigNum": Defines the glyphs for drawing big numbers
    """
    if chrset == "ProcessBar":
        inst_1 = [0x1B, 0x26, 0x01]
        inst_2 = [0x20, 0x25, 0x05]
        
        glyph_0 = [0xFF, 0xFF, 0x41, 0x41, 0x41]    # at address 0x20
        glyph_1 = [0x41, 0x41, 0x41, 0x41, 0x41]    # at address 0x21
        glyph_2 =[0x41, 0x41, 0x41, 0xFF, 0xFF]    # at address 0x22
        glyph_3 =[0xFF, 0xFF, 0x41, 0x5D, 0x5D]    # at address 0x23
        glyph_4 =[0x5D, 0x5D, 0x5D, 0x5D, 0x5D]    # at address 0x24
        glyph_5 =[0x5D, 0x5D, 0x41, 0xFF, 0xFF]    # at address 0x25
        
        print("Downloading special characters for Process Bar...")
        
        SendOverSerial("DISP", "cmd", inst_1)
        SendOverSerial("DISP", "cmd", inst_2)
        SendOverSerial("DISP", "cmd", glyph_0)
        SendOverSerial("DISP", "cmd", glyph_1)
        SendOverSerial("DISP", "cmd", glyph_2)
        SendOverSerial("DISP", "cmd", glyph_3)
        SendOverSerial("DISP", "cmd", glyph_4)
        SendOverSerial("DISP", "cmd", glyph_5)
        
    elif chrset == "BigNum":
        inst_1 = [0x1B, 0x26, 0x01]
        inst_2 = [0x20, 0x28, 0x05]

        glyph_0 = [0xFF, 0xFF, 0x40, 0x40, 0x40]    # at address 0x20
        glyph_1 = [0x40, 0x40, 0x40, 0xFF, 0xFF]    # at address 0x21
        glyph_2 = [0xFF, 0xFF, 0x01, 0x01, 0x01]    # at address 0x22
        glyph_3 = [0xFF, 0xFF, 0x00, 0x00, 0x00]    # at address 0x23
        glyph_4 = [0x60, 0x60, 0x40, 0x40, 0x40]    # at address 0x24
        glyph_5 = [0x03, 0x03, 0x01, 0x01, 0x01]    # at address 0x25
        glyph_6 = [0xFF, 0xFF, 0x41, 0x41, 0x41]    # at address 0x26
        glyph_7 = [0x41, 0x41, 0x41, 0x41, 0x41]    # at address 0x27
        glyph_8 = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF]    # at address 0x28
        glyph_9 = [0x00, 0x00, 0x00, 0x00, 0x00]    # at address 0x29 
        
        print("Downloading special characters for Big Numbers...")
        
        SendOverSerial("DISP", "cmd", inst_1)
        SendOverSerial("DISP", "cmd", inst_2)
        SendOverSerial("DISP", "cmd", glyph_0)
        SendOverSerial("DISP", "cmd", glyph_1)
        SendOverSerial("DISP", "cmd", glyph_2)
        SendOverSerial("DISP", "cmd", glyph_3)
        SendOverSerial("DISP", "cmd", glyph_4)
        SendOverSerial("DISP", "cmd", glyph_5)
        SendOverSerial("DISP", "cmd", glyph_6)
        SendOverSerial("DISP", "cmd", glyph_7)
        SendOverSerial("DISP", "cmd", glyph_8)
        SendOverSerial("DISP", "cmd", glyph_9)

def SelectUsrCharSet(val):
    """
    Selects or deselect the user deined characters. When selected user defined chars are used.
    When deselected the default char set is used.
    Parameters:
        val = 1: user defined characters in used
        val = 0: default characters in use
    """
    if val == 0:
        inst = [0x1B, 0x25, 0x00]
        print("Default character set is in use.")
        SendOverSerial("DISP", "cmd", inst)
    elif val == 1:
        inst = [0x1B, 0x25, 0x1F]
        print("User defined character set is in use.")
        SendOverSerial("DISP", "cmd", inst)
    else:
        print("Error: Invalid command!")
   
def WriteBigNum(pos, num):
    """
    Writes big format numbers to the spcified position. Number arrays conatins the memory address
    of the glyphs building up the number. 4 glyps build up a number.  First two element in the top 
    row of the number. Last two element is the bottom row of the number. 
    parameters:
        pos: horisontal postion on the display to draw the number from. Possible values: from 1-19.
        num: number to be displayed. Possible values: from 0-9.
    """
    one = [0x7F, 0x23, 0x7F, 0x23]
    two = [0x24, 0x21, 0x26, 0x27]
    three = [0x24, 0x21, 0x25, 0x28]
    four = [0x22, 0x25, 0x7F, 0x23]
    five = [0x26, 0x27, 0x25, 0x28]
    six = [0x26, 0x27, 0x26, 0x28]
    seven = [0x24, 0x21, 0x7F, 0x23]
    eight = [0x26, 0x21, 0x26, 0x28]
    nine = [0x26, 0x21, 0x7F, 0x21]  
    zero = [0x20, 0x21, 0x22, 0x28]
    
    if num == 1:
        CrsrSetToPos(pos, 1)
        SendOverSerial("DISP", "cmd", one[0].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", one[1].to_bytes(1,'big'))
        CrsrSetToPos(pos, 2)
        SendOverSerial("DISP", "cmd", one[2].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", one[3].to_bytes(1,'big'))
    elif num == 2:
        CrsrSetToPos(pos, 1)
        SendOverSerial("DISP", "cmd", two[0].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", two[1].to_bytes(1,'big'))
        CrsrSetToPos(pos, 2)
        SendOverSerial("DISP", "cmd", two[2].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", two[3].to_bytes(1,'big'))
    elif num == 3:
        CrsrSetToPos(pos, 1)
        SendOverSerial("DISP", "cmd", three[0].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", three[1].to_bytes(1,'big'))
        CrsrSetToPos(pos, 2)
        SendOverSerial("DISP", "cmd", three[2].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", three[3].to_bytes(1,'big'))
    elif num == 4:
        CrsrSetToPos(pos, 1)
        SendOverSerial("DISP", "cmd", four[0].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", four[1].to_bytes(1,'big'))
        CrsrSetToPos(pos, 2)
        SendOverSerial("DISP", "cmd", four[2].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", four[3].to_bytes(1,'big'))
    elif num == 5:
        CrsrSetToPos(pos, 1)
        SendOverSerial("DISP", "cmd", five[0].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", five[1].to_bytes(1,'big'))
        CrsrSetToPos(pos, 2)
        SendOverSerial("DISP", "cmd", five[2].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", five[3].to_bytes(1,'big'))
    elif num == 6:
        CrsrSetToPos(pos, 1)
        SendOverSerial("DISP", "cmd", six[0].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", six[1].to_bytes(1,'big'))
        CrsrSetToPos(pos, 2)
        SendOverSerial("DISP", "cmd", six[2].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", six[3].to_bytes(1,'big'))
    elif num == 7:
        CrsrSetToPos(pos, 1)
        SendOverSerial("DISP", "cmd", seven[0].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", seven[1].to_bytes(1,'big'))
        CrsrSetToPos(pos, 2)
        SendOverSerial("DISP", "cmd", seven[2].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", seven[3].to_bytes(1,'big'))
    elif num == 8:
        CrsrSetToPos(pos, 1)
        SendOverSerial("DISP", "cmd", eight[0].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", eight[1].to_bytes(1,'big'))
        CrsrSetToPos(pos, 2)
        SendOverSerial("DISP", "cmd", eight[2].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", eight[3].to_bytes(1,'big'))
    elif num == 9:
        CrsrSetToPos(pos, 1)
        SendOverSerial("DISP", "cmd", nine[0].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", nine[1].to_bytes(1,'big'))
        CrsrSetToPos(pos, 2)
        SendOverSerial("DISP", "cmd", nine[2].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", nine[3].to_bytes(1,'big'))
    elif num == 0:
        CrsrSetToPos(pos, 1)
        SendOverSerial("DISP", "cmd", zero[0].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", zero[1].to_bytes(1,'big'))
        CrsrSetToPos(pos, 2)
        SendOverSerial("DISP", "cmd", zero[2].to_bytes(1,'big'))
        SendOverSerial("DISP", "cmd", zero[3].to_bytes(1,'big'))
    else:
        print("Error: invalid number!")
        
def ProcBar(segment):
    prec_0 = [0x20, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x22]
    prec_10 =[0x23, 0x24, 0x24, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x22]
    prec_20 =[0x23, 0x24, 0x24, 0x24, 0x24, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x22]
    prec_30 =[0x23, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x22]
    prec_40 =[0x23, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x22]
    prec_50 =[0x23, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x22]
    prec_60 =[0x23, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x21, 0x21, 0x21, 0x21, 0x21, 0x21, 0x22]
    prec_70 =[0x23, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x21, 0x21, 0x21, 0x21, 0x22]
    prec_80 =[0x23, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x21, 0x21, 0x22]
    prec_90 =[0x23, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x22]
    prec_100 =[0x23, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x25]
    
    if segment == 0:
        CrsrSetToPos(1, 2)
        SendOverSerial("DISP", "cmd", prec_0)
    elif segment == 10:
        CrsrSetToPos(1, 2)
        SendOverSerial("DISP", "cmd", prec_10)
    elif segment == 20:
        CrsrSetToPos(1, 2)
        SendOverSerial("DISP", "cmd", prec_20)
    elif segment == 30:
        CrsrSetToPos(1, 2)
        SendOverSerial("DISP", "cmd", prec_30)
    elif segment == 40:
        CrsrSetToPos(1, 2)
        SendOverSerial("DISP", "cmd", prec_40)
    elif segment == 50:
        CrsrSetToPos(1, 2)
        SendOverSerial("DISP", "cmd", prec_50)
    elif segment == 60:
        CrsrSetToPos(1, 2)
        SendOverSerial("DISP", "cmd", prec_60)
    elif segment == 70:
        CrsrSetToPos(1, 2)
        SendOverSerial("DISP", "cmd", prec_70)
    elif segment == 80:
        CrsrSetToPos(1, 2)
        SendOverSerial("DISP", "cmd", prec_80)
    elif segment == 90:
        CrsrSetToPos(1, 2)
        SendOverSerial("DISP", "cmd", prec_90)
    elif segment == 100:
        CrsrSetToPos(1, 2)
        SendOverSerial("DISP", "cmd", prec_100)        
        
def ClearBigNumPos(pos):
    """
    Clears the display position of a big number. Takes the pos as the horisontal poistion on the screen and writes
    ' ' to it and the next position. Then jumps the same poition on the second line and do the same. ' ' is taken from the 
    big num number 1 first glyph in the first and second row.
    parameters:
        pos: horisontal postion on the display to draw the number from. Possible values: from 1-19.
    """
    one = [0x7F, 0x23, 0x7F, 0x23]
    CrsrSetToPos(pos, 1)
    SendOverSerial("DISP", "cmd", one[0].to_bytes(1,'big'))
    SendOverSerial("DISP", "cmd", one[0].to_bytes(1,'big'))
    CrsrSetToPos(pos, 2)
    SendOverSerial("DISP", "cmd", one[0].to_bytes(1,'big'))
    SendOverSerial("DISP", "cmd", one[0].to_bytes(1,'big'))
    
def WriteScreen(content, pos, line):
    """
    Writes a string to the display
    parameters:
        content: text string to write to the screen
        line: line to write text. Could be 1 or 2
        pos: position in the line. Could be 1 to 20
    """
    CrsrSetToPos(pos, line)
    SendOverSerial("DISP", "text", content)

######################################
#	OBD / ELM327 FUNCTION DEFINITIONS 
######################################
def PollOBDPort(t):
    """
    Function is executed every timer interrupt (600ms). (Note: nincs print a callback funckioban...!!!)
    """
    global rqstPoll
    rqstPoll = True

def ResetOBDBoard():
    """
    Complete reset of ELM board
    parameters:
        None
    """
    cmd = "ATZ\r\n"
    print('\n')
    print("OBD board reset...")
    SendOverSerial("ELM", "AT", cmd)
    time.sleep(3)
    
def ReadVoltage():
    """
    Returns back the supply voltage that is seen by the ELM327 board (=battery voltage)
    parameters:
        None.
    """
    #print('\n')
    #print("Data req.: Battery voltage:")
    cmd = "ATRV\r\n"
    SendOverSerial("ELM", "AT", cmd)
    reply = None
    reply = ReadOBDBoard()
    decoded_reply = reply.decode()
    formatted_reply = decoded_reply.rstrip(decoded_reply[-1])
    print("\tSERIAL in <- OBD: " + str(formatted_reply))
    return formatted_reply

def RestoreVoltageReading():
    print('\n')
    print("Restore voltage reading to factory default calibration:")
    cmd = "ATCV0000\r"
    SendOverSerial("ELM", "AT", cmd)
    reply = ReadOBDBoard()
    print("\tSERIAL in <- OBD: " + str(reply))
    print("Voltage reading is set to factorydefault...")
    time.sleep(1)
    
def CalibrateVoltage(voltage):
    print('\n')
    print("Calibrating voltage to " + str(voltage))
    #vparam=str(voltage)
    #cvparam=vparam.encode("ascii")
    #cmd = "ATCV" + str(voltage) +"\r"
    cmd = "ATCV1265\r"
    SendOverSerial("ELM", "AT", cmd)
    time.sleep(0.1)
    reply = ReadOBDBoard()
    print("\tSERIAL in <- OBD: " + str(reply))
    
def OBDEcho(ena):
    if ena == "ON":
        print('\n')
        print("OBD cmd echo is ON")
        cmd = "ATE1\r\n"
        SendOverSerial("ELM", "AT", cmd)
        reply = ReadOBDBoard()
        print("\tSERIAL in <- OBD: " + str(reply))
    elif ena == "OFF":
        print('\n')
        print("OBD cmd echo is OFF")
        cmd = "ATE0\r\n"
        SendOverSerial("ELM", "AT", cmd)

def OBDLineFeed(ena):
    if ena == "ON":
        print('\n')
        print("OBD linefeed is ON")
        cmd = "ATL1\r\n"
        SendOverSerial("ELM", "AT", cmd)
        reply = ReadOBDBoard()
        print("\tSERIAL in <- OBD: " + str(reply))
    elif ena =="OFF":
        print('\n')
        print("OBD linefeed is OFF")
        cmd = "ATL0\r\n"
        SendOverSerial("ELM", "AT", cmd)
        reply = ReadOBDBoard()
        print("\tSERIAL in <- OBD: " + str(reply))
    
def ReadOBDDevDesc():
    """
    Return ELM board device description (OBD Solutions LLC).
    parameters:
        None
    """
    cmd = "AT@1\r\n"
    print('\n')
    print("Data req.: OBD Device ID:")
    SendOverSerial("ELM", "AT", cmd)
    reply = ReadOBDBoard()
    print("\tSERIAL in <- OBD: " + str(reply))
    
def ReadOBDVerID():
    """
    Returns ELM board internal firmvare version.
    parameters:
        None
    """
    cmd = "ATI\r\n"
    print('\n')
    print("Reading OBD board version ID:")
    SendOverSerial("ELM", "AT", cmd)
    reply = ReadOBDBoard()
    decoded_reply = " " + reply.decode()
    print("\tSERIAL in <- OBD: " + decoded_reply)
    return decoded_reply

def InitCarComm():
    """
    Initiates last working communication protocol used by ECU.
    parameters:
        None
    """
    cmd = "ATSP0\r\n"
    print('\n')
    print("Init/reset comm protocol for vehicle communication:")
    SendOverSerial("ELM", "AT", cmd)
    reply = ReadOBDBoard()
    print("\tSERIAL in <- OBD: " + str(reply))
    
def ShowCurrentProtocol():
    """
    Returns the currently selected communication protocol.
    parameters :
        none
    """
    cmd = "ATDP\r\n"
    print('\n')
    SendOverSerial("ELM", "AT", cmd)
    reply = ReadOBDBoard()
    print("\tSERIAL in <- OBD: " + str(reply))
    
def KWPFastInit():
    """
    Request Fast Initiation procedure for KWP protocol
    parameters:
        none
    """
    cmd = "ATFI\r\n"
    print('\n')
    print("KWP fast init requested")
    SendOverSerial("ELM", "AT", cmd)
    reply = ReadOBDBoard()
    print("\tSERIAL in <- OBD: " + str(reply))

def RqstKWPKeyWrds():
    """
    Requests and returns used OBD keywords used by ECU. Possible responses:
    "SEARCHING... -> ommunication with car ECU has been started... 
    "STOPPED" -> Communication is interrupted by something...
    "hex numbers, like: 41 00 xx xx xx xx -> Valid response by car ECU. xx numbers are hex numbers. COnverting them to binary, will tell what PIDS are suported. See wiki OBD2 page eg...
    parameters:
        None
    """
    pid = "0100\r\n"
    print('\n')
    print("Requesting protocol keywords:")
    SendOverSerial("ELM", "AT", pid)
    time.sleep(0.05)
    reply1 = ReadOBDBoard()
    print("\tSERIAL in <- OBD: " + str(reply1))
    time.sleep(5)
    reply2 = ReadOBDBoard()
    print("\tSERIAL in <- OBD: " + str(reply2))

def RqstRPM():
    """
    Requests and returns actual engine rpm value from car ECU
    parameters:
        None
    """
    pid = "010C01\r\n"          # last byte (0x01) meainin only one line is expected as rsponse -> makes ELM raction amd communication faster
    #print('\n')
    print("Requesting engine RPM value")
    SendOverSerial("ELM", "AT", pid)
    time.sleep(0.02)
    rpm = ReadOBDBoard()
    print("\tSERIAL in <- OBD: " + str(rpm))
    return(rpm)

def RqstSpeed():
    """
    Requests and returns actual speed value from car ECU
    parameters:
        None
    """
    pid = "010D01\r\n"          # last byte (0x01) meainin only one line is expected as rsponse -> makes ELM raction amd communication faster	
    #print('\n')
    print("Requesting car speed value")
    SendOverSerial("ELM", "AT", pid)
    time.sleep(0.02)
    speed = ReadOBDBoard()
    print("\tSERIAL in <- OBD: " + str(speed))
    return(speed)

def RqstVBat():
    """
    NOT SUPPORTED BY TOYOTA RAV4 XA20
    Requests and returns actual battery voltage meadured by the ECU. (IF PID SUPPORTED ONLY)
    parameters:
        None
    """
    voltage = 0
    pid = "014201\r\n"
    #print('\n')
    print("Requesting control module voltage")
    SendOverSerial("ELM", "AT", pid)
    response = bytearray(ReadOBDBoard())
    response = response.split()
    A = int(response[3].decode(),16)
    B = int(response[4].decode(),16)
    voltage = str((256*A)/B)
    print("Control module voltage is: " + voltage)
    return voltage

def ReadOBDBoard():
    ErrCntr = 0
    evalString1 = "UNABLE TO CONNECT"
    evalString2 = "OK"
    evalString3 = "?"
    resp = None
    
    #print(evalString1)
    #print(str(evalString1))
    #print(type(evalString1))
    #print(evalString1)
    
    resp = OBD.readline()
    #print(type(resp))
    decoded_resp = resp.decode('utf-8')
    #print(type(decoded_resp))
    #print("Decode response is: "+ decoded_resp)
    
    if type(resp) is type(None):
        print("OBD: No response...")
        
        while (ErrCntr < 3):
            ErrCntr = ErrCntr + 1
            print("Repeating command. Attemp: " + str(ErrCntr))
            RepeateCmd()
            resp = OBD.readline()
            if resp == None:
                continue
            elif resp == "?":
                continue
            else:
                break
        if (ErrCntr == 3):
            ErrCntr = 0
            ReleaseOBDBoardwErrMsg("ELM")
            
    if (decoded_resp == evalString3):			# ?
        print("OBD: Command not understood. Repeating...")
        if cntr == 4:
            cntr = 0
            ReleaseOBDBoardwErrMsg("ELM")
        else:
            cntr = cntr + 1
            print("error count = " + str(cntr))
            RepeateCmd()
            
    elif (decoded_resp == evalString1):							# UNABLE TO CONNECT
        print("case no connect")
        ReleaseOBDBoardwErrMsg("CAR")
        
    elif (decoded_resp == evalString2):		# OK
        print("case OK")
        return(resp)
    
    else:
        print("nocase")
        return(resp)

def RepeateCmd():
    """
    Repeats last sent command to ELM board by sending "\r".
    parameters:
        None
    """
    enter = "\r"
    SendOverSerial("ELM", "AT", enter)

###############################
#	SYSTEM FUNCTION DEFINITIONS
###############################
def ReleaseOBDBoardwErrMsg(source):
    if source == "ELM":
        ElmEna("OFF")
        ClrScrn()
        WriteScreen(ERROR, 1, 1)
        WriteScreen(ErrStr_0, 1, 2)
        SetBlinkDisplay(20)
        sys.exit()
    elif source == "CAR":
        ElmEna("OFF")
        ClrScrn()
        WriteScreen(ERROR, 1, 1)
        WriteScreen(ErrStr_1, 1, 2)
        SetBlinkDisplay(20)
        sys.exit()

def CalculateDispBrightnessLevel():
    level = 1
    potVal = pot.read_u16()
    if (potVal) <= 16384:
        level = 1
        return level
    elif (potVal > 16384 and potVal <= 32768):
        level = 2
        return level
    elif (potVal > 32768 and potVal <= 49152):
        level = 3
        return level
    elif (potVal > 49152 and potVal < 65536):
        level = 4
        return level
    
def InitDevice():
    #Display init and eye candy
    ClrScrn()
    SetBlinkDisplay(0)						# Turn off Scrren blinling if it was set due to error msg
    DispInit()
    DefineChars("ProcessBar")
    time.sleep(1)
    SelectUsrCharSet(0)
    
    time.sleep(1)
   # WriteScreen(loading, 6, 1)
    WriteScreen(initStr_0, 1, 1)			# STARTING (pos 1 line 1)
    SelectUsrCharSet(1)
    time.sleep(0.1)
    ProcBar(0)
    time.sleep(0.5)
    SelectUsrCharSet(0)
    time.sleep(0.1)
    ClrCrsrLine(1)
    WriteScreen(initStr_1, 1, 1)			# DISP INIT
    SelectUsrCharSet(1)
    time.sleep(0.1)
    ProcBar(20)
    time.sleep(0.5)
    SelectUsrCharSet(0)
    ClrCrsrLine(1)
    WriteScreen(initStr_2, 1, 1)			# OBD Board ENA -> connecting 12V and K lne to ELM327 Board (pos 1 line 2)
    time.sleep(0.5)
    SelectUsrCharSet(1)
    ProcBar(30)
    ElmEna("ON")							# Relay -> ON power up ELM board a connect comm. line
    time.sleep(2)							# Give some time the ELM board too boot...
    ProcBar(40)
    SelectUsrCharSet(0)
    ClrCrsrLine(1)
    WriteScreen(initStr_3, 1, 1)			# OBD BOARD INIT -> configure ELM32 board behaviour (pos 1 line 2)
    OBDEcho("OFF")							# ATE0: Don't repeat commands
    time.sleep(0.5)
    OBDLineFeed("OFF")						# ATL0: Don't put line feed after ELM327 board response message
    time.sleep(0.5)
    SelectUsrCharSet(1)
    data = ReadOBDVerID()	                # ATI
    ProcBar(60)
    SelectUsrCharSet(0)
    ClrCrsrLine(1)
    WriteScreen(data, 1, 1)
    time.sleep(0.5)
    SelectUsrCharSet(1)
    ProcBar(70)
    time.sleep(0.5)
    SelectUsrCharSet(0)
    ClrCrsrLine(1)
    WriteScreen(initStr_4, 1, 1)			# INIT CAR COM...
    SelectUsrCharSet(1)
    ProcBar(80)
    
    #InitCarComm()
    InitCarComm()							# ATSP0
    time.sleep(3)
    ShowCurrentProtocol()                   # ATDP
    time.sleep(2)
    RqstKWPKeyWrds()
    time.sleep(3)
    ProcBar(90)
    time.sleep(0.5)
    SelectUsrCharSet(0)
    ClrCrsrLine(1)
    WriteScreen(initStr_5, 1, 1)			# MAIN SCRN INIT...
    SelectUsrCharSet(1)
    ProcBar(100)
    time.sleep(0.5)
    
    #Draw main screen
    ClrScrn()
    SelectUsrCharSet(0)
    WriteScreen(kmh, 7, 1)
    #WriteScreen(vb, 13, 1)
    #WriteScreen(brkt, 8, 2)
    WriteScreen(rpm, 18, 2)
    DefineChars("BigNum")
    SelectUsrCharSet(1)
    #RestoreVoltageReading()
    #CalibrateVoltage(1265)

    """SET POLLING INTERVAL AND PRINT OUT MAIN UI """
    #global tick

    flgInitReady = 1
    
#####################
#	PROGARM START	#
#####################
try:
    InitDevice()

    tick = Timer()
    tick.init(mode=Timer.PERIODIC, period=300, callback=PollOBDPort)	# define periodic timer with 500ms to use continous data poll

    while True:
        #print("in main...")
        #print("tickCount =" + str(tickCount))
        #print(rqstPoll)
        
        DispBrightness = CalculateDispBrightnessLevel()
        if (DispBrightness != DispBrightness_old):
            SetBrigntness(DispBrightness)
            DispBrightness_old = DispBrightness
        else:
            pass
        
        if (rqstPoll == True):
            tickCount = tickCount + 1
            if tickCount > 2:
                print("ticCount overflow -> reset")
                tickCount = 1
            if (tickCount == 1):									# Requesting speed and rpm data. Response is a series of bytes: b'41 0D 00 \r\r
                dataMsgSpd = bytearray(RqstSpeed())					# Saves response to a byte array
                dataMsgSpd = dataMsgSpd.split()						# Splits response to a list, separator is default (=space)
                Spd = str(round(int(dataMsgSpd[2].decode(),16)))	# Speed value is stored in [2] element. It is hexadecimal value converted to int
                print(Spd)
               # print("len Spd is: " + str(len(Spd)))
                SelectUsrCharSet(1)
                
                if (len(Spd) == 2):
                    ClearBigNumPos(1)
                    for i in range(len(Spd)):
                        for number in range(10):    
                            if (int(Spd[i]) == number):
                                if i == 0:
                                    WriteBigNum(3, number)
                                elif i == 1:
                                    WriteBigNum(5, number)
                    
                elif (len(Spd) == 1):
                    for i in range(len(Spd)):
                        for number in range(10):
                            #print("i is: " + str(i) + " actual number is: " + str(number))
                            #print("Spd[i] is :" + str(Spd[i]))
                            if (int(Spd[i]) == number):
                                if i == 0:
                                    ClearBigNumPos(1)
                                    ClearBigNumPos(3)
                                    WriteBigNum(5, number)
                else:
                    for i in range(len(Spd)):
                        for number in range(10):    
                            if (int(Spd[i]) == number):
                                if i == 0:
                                    WriteBigNum(1, number)
                                elif i == 1:
                                    WriteBigNum(3, number)
                                elif i == 2:
                                    WriteBigNum(5, number)
                
                rqstPoll = False
                
            elif (tickCount == 2):
                dataMsgRPM = bytearray(RqstRPM())
                dataMsgRPM = dataMsgRPM.split()
                A = int(dataMsgRPM[2].decode(),16)
                B = int(dataMsgRPM[3].decode(),16)
                rpm = str(round((256*A + B) / 4))
                print(rpm)
                SelectUsrCharSet(0)
                WriteScreen(clrRPM, 14, 2)
                if (len(rpm) == 4):
                    WriteScreen(rpm, 14, 2)
                elif (len(rpm) == 3):
                    WriteScreen(rpm, 15, 2)
                elif (len(rpm) == 2):
                    WriteScreen(rpm, 16, 2)
                elif (len(rpm) == 1):
                    WriteScreen(rpm, 17, 2)
                secCount = secCount + 1
                tickCount = 0
                
                if annuFlg == True:
                    AnnunciatorOnOff(20, "ON")
                    annuFlg = False
                elif annuFlg == False:
                    AnnunciatorOnOff(20, "OFF")
                    annuFlg = True
                rqstPoll = False
                
            if secCount == 10:						# Requesting battery voltage 
                uBat = ReadVoltage()
                print(str(uBat))
                secCount = 0
        else:
            pass
            #print("in pass...")
        """    
        for i in range(10):
            WriteBigNum(1,i)
            time.sleep(0.1)
            WriteScreen(str(i), 15, 2)
            for j in range(10):
                WriteBigNum(3,j)
                time.sleep(0.1)
                WriteScreen(str(j), 16, 2)
                for k in range(10):
                    WriteBigNum(5,k)
                    time.sleep(0.1)
                    WriteScreen(str(k), 17, 2)
        """
except KeyboardInterrupt:
   tick.deinit()
   print("Closing Serial ports...")
   VFD.deinit()
   OBD.deinit()
   print("Done...")
   print("Disconnecting ELM327 module...")
   ElmEna("OFF")
   print("Done...")

except SystemExit:
    if (flgInitReady == 1):
        tick.deinit()
        flgInitReady = 0
    print("Stopping with Error (Caught sys.exit)...")
    print("Closing Serial ports...")
    VFD.deinit()
    OBD.deinit()
    print("Done...")
    print("Exit main.py")
