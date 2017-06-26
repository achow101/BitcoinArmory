from PyQt4.Qt import * #@UnusedWildImport
from PyQt4.QtGui import * #@UnusedWildImport
from qtdefines import * #@UnusedWildImport

import hid
import struct
import json
import base64
import pyaes
import hashlib
import os

# Functions necessarily to send data to Digital Bitbox. 
# Modified versions of https://github.com/digitalbitbox/mcu/blob/master/py/dbb_utils.py
applen = 225280 # flash size minus bootloader length
chunksize = 8*512
usb_report_size = 64 # firmware > v2.0
report_buf_size = 4096 # firmware v2.0.0
boot_buf_size_send = 4098
boot_buf_size_reply = 256
HWW_CID = 0xFF000000
HWW_CMD = 0x80 + 0x40 + 0x01


def aes_encrypt_with_iv(key, iv, data):
    aes_cbc = pyaes.AESModeOfOperationCBC(key, iv=iv)
    aes = pyaes.Encrypter(aes_cbc)
    e = aes.feed(data) + aes.feed()  # empty aes.feed() appends pkcs padding
    return e


def aes_decrypt_with_iv(key, iv, data):
    aes_cbc = pyaes.AESModeOfOperationCBC(key, iv=iv)
    aes = pyaes.Decrypter(aes_cbc)
    s = aes.feed(data) + aes.feed()  # empty aes.feed() strips pkcs padding
    return s


def EncodeAES(secret, s):
    iv = bytes(os.urandom(16))
    ct = aes_encrypt_with_iv(secret, iv, s)
    e = iv + ct
    return base64.b64encode(e)


def DecodeAES(secret, e):
    e = bytes(base64.b64decode(e))
    iv, e = e[:16], e[16:]
    s = aes_decrypt_with_iv(secret, iv, e)
    return s


def sha256(x):
    return hashlib.sha256(x).digest()


def Hash(x):
    if type(x) is unicode: x=x.encode('utf-8')
    return sha256(sha256(x))

def send_frame(data, device):
    data = bytearray(data)
    data_len = len(data)
    seq = 0;
    idx = 0;
    write = []
    while idx < data_len:
        if idx == 0:
            # INIT frame
            write = data[idx : idx + min(data_len, usb_report_size - 7)]
            device.write('\0' + struct.pack(">IBH",HWW_CID, HWW_CMD, data_len & 0xFFFF) + write + '\xEE' * (usb_report_size - 7 - len(write)))
        else: 
            # CONT frame
            write = data[idx : idx + min(data_len, usb_report_size - 5)]
            device.write('\0' + struct.pack(">IB", HWW_CID, seq) + write + '\xEE' * (usb_report_size - 5 - len(write)))
            seq += 1
        idx += len(write)


def read_frame(device):
    # INIT response
    read = device.read(usb_report_size)
    cid = ((read[0] * 256 + read[1]) * 256 + read[2]) * 256 + read[3]
    cmd = read[4]
    data_len = read[5] * 256 + read[6]
    data = read[7:]
    idx = len(read) - 7;
    while idx < data_len:
        # CONT response
        read = device.read(usb_report_size)
        data += read[5:]
        idx += len(read) - 5
    assert cid == HWW_CID, '- USB command ID mismatch'
    assert cmd == HWW_CMD, '- USB command frame mismatch'
    return data

def send_plain(msg, device):
    reply = ""
    try:
        serial_number = device.get_serial_number_string()
        if serial_number == "dbb.fw:v2.0.0" or serial_number == "dbb.fw:v1.3.2" or serial_number == "dbb.fw:v1.3.1":
            device.write('\0' + bytearray(msg) + '\0' * (report_buf_size - len(msg)))
            r = []
            while len(r) < report_buf_size:
                r = r + device.read(report_buf_size)
        else:
            send_frame(msg, device)
            r = read_frame(device)
        r = str(bytearray(r)).rstrip(' \t\r\n\0')
        r = r.replace("\0", '')
        reply = json.loads(r)
    except Exception as e:
        print 'Exception caught while sending plaintext message to DigitalBitbox ' + str(e)
    return reply

def send_encrypt(msg, password, device):
    print "Sending: {}".format(msg)
    reply = ""
    try:
        secret = Hash(password)
        msg = EncodeAES(secret, msg)
        reply = send_plain(msg, device)
        if 'ciphertext' in reply:
            reply = DecodeAES(secret, ''.join(reply["ciphertext"]))
            print "Reply:   {}\n".format(reply)
            reply = json.loads(reply)
        if 'error' in reply:
            password = None
            print "\n\nReply:   {}\n\n".format(reply)
    except Exception as e:
        print 'Exception caught ' + str(e)
    return reply

# Choose the Digital Bitbox to setup
################################################################################
class DlgChooseDigitalBitbox(ArmoryDialog):
   #############################################################################
   def __init__(self, parent, main):
      super(DlgChooseDigitalBitbox, self).__init__(parent, main)

      lblDescr = QRichLabel(self.tr(
      '<b><u>Choose a Digital Bitbox to Setup</u></b> '
      '<br><br>'
      'Use this window to setup choose which Digital Bitbox hardware wallet '
      'to setup.'))


      lblType = QRichLabel(self.tr('<b>Available Devices:</b>'), doWrap=False)

      self.rdoBtnGrp = QButtonGroup()
      layoutRadio = QVBoxLayout()
      layoutRadio.setSpacing(0) 

      transports = hid.enumerate()
      self.devices = []
      id = 0
      for d in transports:
         if d['vendor_id'] == 0x03eb and d['product_id'] == 0x2402:
            if d['interface_number'] == 0 or d['usage_page'] == 0xffff:
               # hidapi is not consistent across platforms
               # usage_page works on Windows/Mac; interface_number works on Linux

               # Open connection to device
               device = hid.device()
               device.open_path(d['path'])

               # Check if it has a password on it
               reply = send_plain('{"ping":""', device)
               if 'ping' not in reply:
                  self.has_password = False
               elif reply['ping'] == 'password':
                  self.has_password = True

               if self.has_password:
                  rdo = QRadioButton(self.tr("Digital Bitbox [Initialized]"))
               else:
                  rdo = QRadioButton(self.tr("Digital Bitbox [Uninitialized]"))

               self.rdoBtnGrp.addButton(rdo)
               self.rdoBtnGrp.setId(rdo, id)
               id += 1
               rdo.setChecked(True)
               layoutRadio.addWidget(rdo)
               self.devices.append(device)

      radioButtonFrame = QFrame()
      radioButtonFrame.setLayout(layoutRadio)

      self.btnAccept = QPushButton(self.tr('Next'))
      self.btnCancel = QPushButton(self.tr("Cancel"))
      self.connect(self.btnAccept, SIGNAL(CLICKED), self.nextDlg)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnAccept, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)

      layout = QVBoxLayout()
      layout.addWidget(radioButtonFrame)
      layout.addWidget(buttonBox)
      self.setLayout(layout)

      self.setWindowTitle(self.tr('Choose a Digital Bitbox to Setup'))

      self.setMinimumWidth(500)
      self.layout().setSizeConstraint(QLayout.SetFixedSize)

   def nextDlg(self):
      idx = self.rdoBtnGrp.checkedId()
      print idx
      if self.has_password:
         dlg = DlgCreateDigitalBitboxWallet(self.parent, self.main, self.devices[idx])
      else:
         dlg = DlgSetupDigitalBitbox(self.parent, self.main, self.devices[idx])

      self.accept()
      dlg.exec_()

# Setup the wallet for an initialized KeepKey
class DlgCreateDigitalBitboxWallet(ArmoryDialog):
   def __init__(self, parent, main, device):
      super(DlgCreateDigitalBitboxWallet, self).__init__(parent, main)
      self.device = device


# Setup an uninitialized KeepKey
class DlgSetupDigitalBitbox(ArmoryDialog):
   def __init__(self, parent, main, device):
      super(DlgSetupDigitalBitbox, self).__init__(parent, main)
      self.device = device

# Need to put circular imports at the end of the script to avoid an import deadlock
from qtdialogs import CLICKED