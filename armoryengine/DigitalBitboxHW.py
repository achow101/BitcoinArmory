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
        print msg
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
               reply = send_plain('{"ping":""}', device)
               self.has_password = False
               if reply['ping'] == 'password':
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
      if self.has_password:
         # Get the passphrase
         dlg = DlgEnterPassphrase(self.parent, self.main, self.devices[idx])
         if dlg.exec_():
            passphrase = str(dlg.edtPasswd.text())
            dlg = DlgSeededDigitalBitbox(self.parent, self.main, self.devices[idx], passphrase)
      else:
         dlg = DlgSetupDigitalBitbox(self.parent, self.main, self.devices[idx])

      self.accept()
      dlg.exec_()

# Setup an uninitialized Digital Bitbox
class DlgSetupDigitalBitbox(ArmoryDialog):
   def __init__(self, parent, main, device):
      super(DlgSetupDigitalBitbox, self).__init__(parent, main)
      self.device = device

      lblDescr = QRichLabel(self.tr(
      '<b><u>Setup a Digital Bitbox</u></b> '
      '<br><br>'
      'Use this window to setup a Digital Bitbox hardware wallet '
      'to setup.'))

      lblInstruct = QRichLabel(self.tr('An uninitialized Digital Bitbox is deteced. Enter a '
         'new passphrase in the next window. Remember this passphrase, you cannot access your coins or '
         'the backup without this password. A backup will be made automatically when '
         'the wallet is generated. The passphrase must be more than 4 characters and less than 64 characters.'))

      self.btnAccept = QPushButton(self.tr('Next'))
      self.btnCancel = QPushButton(self.tr("Cancel"))
      self.connect(self.btnAccept, SIGNAL(CLICKED), self.nextDlg)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnAccept, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)

      layout = QVBoxLayout()
      layout.addWidget(lblInstruct)
      layout.addWidget(buttonBox)
      self.setLayout(layout)

      self.setWindowTitle(self.tr('Setup a Digital Bitbox'))

      self.setMinimumWidth(500)
      self.layout().setSizeConstraint(QLayout.SetFixedSize)

   def nextDlg(self):
      dlg = DlgChangePassphrase(self.parent, self.main)
      if dlg.exec_():
         self.accept()
         passphrase = str(dlg.edtPasswd1.text())
         dlg.edtPasswd1.clear()
         dlg.edtPasswd2.clear()

         # Set the password on device
         reply = send_plain('{"password":"' + passphrase + '"}', self.device)

         # Check if the device is seeded
         reply = send_encrypt('{"device":"info"}', passphrase, self.device)
         if reply['device']['id'] <> "":
            dlg = DlgSeededDigitalBitbox(self.parent, self.main, self.device, passphrase) # Already seeded
         else:
            dlg = DlgUnseededDigitalBitbox(self.parent, self.main, self.device, passphrase) # Seed if not initialized

         dlg.exec_()
      else:
         self.reject()

# Seed unseed digital bitbox
# Last dialog, make wallet here and setup the device
class DlgUnseededDigitalBitbox(ArmoryDialog):
   def __init__(self, parent, main, device, passphrase):
      super(DlgUnseededDigitalBitbox, self).__init__(parent, main)
      self.device = device
      self.passphrase = passphrase

      lblDescrTitle = QRichLabel(self.tr('<b><u>Initialize a Digital Bitbox</u></b>'))
      lblDescr = QRichLabel(self.tr('Choose how you want to initialize your Digital Bitbox'))

      self.rdoGenerate = QRadioButton(self.tr('Generate a new random wallet'))
      self.rdoRestore = QRadioButton(self.tr('Load a wallet from the micro SD card'))
      btngrp = QButtonGroup(self)
      btngrp.addButton(self.rdoGenerate)
      btngrp.addButton(self.rdoRestore)
      btngrp.setExclusive(True)

      self.rdoGenerate.setChecked(True)

      self.btnOkay = QPushButton(self.tr('Finish'))
      self.btnCancel = QPushButton(self.tr('Cancel'))
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnOkay, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)
      self.connect(self.btnOkay, SIGNAL(CLICKED), self.finish)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)


      layout = QVBoxLayout()
      layout.addWidget(lblDescrTitle)
      layout.addWidget(lblDescr)
      layout.addWidget(HLINE())
      layout.addWidget(self.rdoGenerate)
      layout.addWidget(self.rdoRestore)
      layout.addWidget(buttonBox)
      self.setLayout(layout)
      self.setMinimumWidth(450)

      self.setWindowTitle(self.tr('Initialize a Digital Bitbox'))

   def finish(self):
      if self.rdoGenerate.isChecked():
         key = self.passphrase # TODO: Stretch key
         filename = "armory_.wallet.pdf" # TODO: Build actual filename from wallet file
         msg = '{"seed":{"source": "create", "key": "%s", "filename": "%s", "entropy": "%s"}}' % (key, filename, 'Digital Bitbox Armory Implementation')
         reply = send_encrypt(msg, self.passphrase, self.device)
         if 'error' in reply:
            QMessageBox.critical(self, self.tr("Device Error"), str(reply['error']['message']), QMessageBox.Close)
         else:
            self.accept()
      elif self.rdoRestore.isChecked():
         dlg = DlgLoadBackup(self.parent, self.main, self.device, self.passphrase, False) # Don't need to show message when restoring to uninitialized device
         dlg.exec_()
         self.accept()

# Already seeded digital bitbox
# Last dialog, make wallet here and setup the device
class DlgSeededDigitalBitbox(ArmoryDialog):
   def __init__(self, parent, main, device, passphrase):
      super(DlgSeededDigitalBitbox, self).__init__(parent, main)
      self.device = device
      self.passphrase = passphrase

      lblDescrTitle = QRichLabel(self.tr('<b><u>Initialize a Digital Bitbox</u></b>'))
      lblDescr = QRichLabel(self.tr('The Digital Bitbox is already seeded. Choose how you want to initialize your Digital Bitbox'))

      self.rdoGenerate = QRadioButton(self.tr('Create a wallet with the current seed'))
      self.rdoRestore = QRadioButton(self.tr('Load a wallet from the micro SD card'))
      self.rdoErase = QRadioButton(self.tr('Erase the Digital Bitbox'))
      btngrp = QButtonGroup(self)
      btngrp.addButton(self.rdoGenerate)
      btngrp.addButton(self.rdoRestore)
      btngrp.addButton(self.rdoErase)
      btngrp.setExclusive(True)

      self.rdoGenerate.setChecked(True)

      self.btnOkay = QPushButton(self.tr('Finish'))
      self.btnCancel = QPushButton(self.tr('Cancel'))
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnOkay, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)
      self.connect(self.btnOkay, SIGNAL(CLICKED), self.finish)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)


      layout = QVBoxLayout()
      layout.addWidget(lblDescrTitle)
      layout.addWidget(lblDescr)
      layout.addWidget(HLINE())
      layout.addWidget(self.rdoGenerate)
      layout.addWidget(self.rdoRestore)
      layout.addWidget(self.rdoErase)
      layout.addWidget(buttonBox)
      self.setLayout(layout)
      self.setMinimumWidth(450)

      self.setWindowTitle(self.tr('Initialize a Digital Bitbox'))

   def finish(self):
      if self.rdoGenerate.isChecked():
         # Use existing seed
         # TODO: Make the Armory wallet file
         self.accept()
      elif self.rdoErase.isChecked():
         confirm = QMessageBox.warning(self, self.tr('Confirm Erase'), \
                  self.tr('Are you sure you want to erase this Digital Bitbox?'), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
         if confirm == QMessageBox.Yes:
            # Show instructions
            box = QMessageBox(QMessageBox.Information, self.tr('Confirm Erase'), self.tr('To continue, touch the Digital Bitbox\'s light for 3 seconds.\n'
               'To cancel, briefly touch the light or wait for the timeout.\n\nPlease wait.'), parent=self)
            box.setModal(True)
            box.show()

            # Perform erase
            reply = send_encrypt('{"reset":"__ERASE__"}', self.passphrase, self.device)
            if 'error' in reply:
               QMessageBox.critical(self, self.tr('Device Error'), reply['error']['message'], QMessageBox.Close)
            else:
               QMessageBox.information(self, self.tr("Device Erase"), self.tr("Device Erased"), QMessageBox.Close)
               self.accept()
            box.done(0)
      elif self.rdoRestore.isChecked():
         dlg = DlgLoadBackup(self.parent, self.main, self.device, self.passphrase)
         self.accept()
         dlg.exec_()


class DlgLoadBackup(ArmoryDialog):
   def __init__(self, parent, main, device, passphrase, show_msg = True):
      super(DlgLoadBackup, self).__init__(parent, main)
      self.device = device
      self.passphrase = passphrase
      self.show_msg = show_msg

      lblDescrTitle = QRichLabel(self.tr('<b><u>Restore a Digital Bitbox</u></b>'))
      lblDescr = QRichLabel(self.tr('Choose a Backup file to restore from'))

      layout = QVBoxLayout()
      layout.addWidget(lblDescrTitle)
      layout.addWidget(lblDescr)
      layout.addWidget(HLINE())

      # Get list of backups
      self.btngrp = QButtonGroup(self)
      self.btngrp.setExclusive(True)
      backup_files = send_encrypt('{"backup":"list"}', self.passphrase, self.device)
      if 'error' in backup_files:
         QMessageBox.critical(self, self.tr("Device Error"), str(backup_files['error']['message']), QMessageBox.Close)
         return
      for f in backup_files['backup']:
         rdo = QRadioButton(f)
         self.btngrp.addButton(rdo)
         rdo.setChecked(True)
         layout.addWidget(rdo)

      self.btnOkay = QPushButton(self.tr('Finish'))
      self.btnCancel = QPushButton(self.tr('Cancel'))
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnOkay, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)
      self.connect(self.btnOkay, SIGNAL(CLICKED), self.finish)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)

      layout.addWidget(buttonBox)
      self.setLayout(layout)
      self.setMinimumWidth(450)

      self.setWindowTitle(self.tr('Initialize a Digital Bitbox'))

   def finish(self):
      dlg = DlgEnterPassphrase(self, self.parent, self.main)
      if dlg.exec_():
         checked = self.btngrp.checkedButton()
         key = dlg.edtPasswd.text() # TODO: key stretch

         if self.show_msg:
            # Show instructions
            box = QMessageBox(QMessageBox.Information, self.tr('Confirm Backup Restore'), self.tr('To continue, touch the Digital Bitbox\'s light for 3 seconds.\n'
               'To cancel, briefly touch the light or wait for the timeout.\n\nPlease wait'), parent=self)
            box.setModal(True)
            box.show()

         # Actually load backup
         msg = '{"seed":{"source": "backup", "key": "%s", "filename": "%s"}}' % (key, checked.text())
         reply = send_encrypt(msg, self.passphrase, self.device)
         if 'error' in reply:
            QMessageBox.critical(self, self.tr("Device Error"), str(reply['error']['message']), QMessageBox.Ok)
         else:
            self.accept()
         box.done(0)

# Dialog to enter passphrase
class DlgEnterPassphrase(ArmoryDialog):
   def __init__(self, parent, main, device):
      super(DlgEnterPassphrase, self).__init__(parent, main)
      self.device = device

      lblDescr = QLabel(self.tr("Enter your passphrase for this Digital Bitbox"))
      lblPasswd = QLabel(self.tr("Passphrase:"))
      self.edtPasswd = QLineEdit()
      self.edtPasswd.setEchoMode(QLineEdit.Password)
      self.edtPasswd.setMinimumWidth(MIN_PASSWD_WIDTH(self))
      self.edtPasswd.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

      self.btnAccept = QPushButton(self.tr("Accept"))
      self.btnCancel = QPushButton(self.tr("Cancel"))
      self.connect(self.btnAccept, SIGNAL(CLICKED), self.accept)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnAccept, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)

      layout = QGridLayout()
      layout.addWidget(lblDescr, 1, 0, 1, 2)
      layout.addWidget(lblPasswd, 2, 0, 1, 1)
      layout.addWidget(self.edtPasswd, 2, 1, 1, 1)

      self.btnAccept = QPushButton(self.tr('Next'))
      self.btnCancel = QPushButton(self.tr("Cancel"))
      self.connect(self.btnAccept, SIGNAL(CLICKED), self.checkPassword)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnAccept, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)
      layout.addWidget(buttonBox, 3, 1, 1, 1)

      self.setLayout(layout)

   def checkPassword(self):
      # Blink LED to make sure password is right
      reply = send_encrypt('{"led":"blink"}', str(self.edtPasswd.text()), self.device)
      if 'error' in reply:
         if reply['error']['code'] == 100:
            QMessageBox.critical(self, self.tr('Incorrect Password'), self.tr('The password you entered was incorrect.'), QMessageBox.Ok)
         else:
            QMessageBox.critical(self, self.tr('Device Error'), str(reply['error']['message']), QMessageBox.Ok)
      else:
         self.accept()

# Need to put circular imports at the end of the script to avoid an import deadlock
from qtdialogs import CLICKED, DlgChangePassphrase, MIN_PASSWD_WIDTH