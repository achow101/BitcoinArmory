from PyQt4.Qt import * #@UnusedWildImport
from PyQt4.QtGui import * #@UnusedWildImport
from qtdefines import * #@UnusedWildImport

from keepkeylib.client import ProtocolMixin, BaseClient
from keepkeylib.transport_hid import HidTransport

import keepkeylib.messages_keepkey_pb2 as proto
import keepkeylib.types_keepkey_pb2 as types
from keepkeylib.qt.pinmatrix import PinMatrixWidget

# GUI Mixin Borrowed from Electrum
class GuiMixin(object):

   def callback_ButtonRequest(self, msg):
      return proto.ButtonAck()

   def callback_PinMatrixRequest(self, msg):
      if msg.type == 2:
         # Entering a new private-key-bearing
         lblInstruct = QLabel(QObject().tr("Enter a new PIN for your KeepKey"))
      elif msg.type == 3:
         lblInstruct = QLabel(QObject().tr("Re-enter the new PIN for your %s.\n\n"
         "NOTE: the positions of the numbers have changed!"))
      else:
         lblInstruct = QLabel(QObject().tr("Enter your current %s PIN:"))

      matrix = DlgPinMatrix(lblInstruct=lblInstruct)
      matrix.exec_()

      pin = matrix.pin

      if not pin:
         return proto.Cancel()
      return proto.PinMatrixAck(pin=pin)

   def callback_PassphraseRequest(self, req):
      if self.creating_wallet:
         msg = _("Enter a passphrase to generate this wallet.  Each time "
               "you use this wallet your %s will prompt you for the "
               "passphrase.  If you forget the passphrase you cannot "
               "access the bitcoins in the wallet.") % self.device
      else:
         msg = _("Enter the passphrase to unlock this wallet:")
      passphrase = self.handler.get_passphrase(msg, self.creating_wallet)
      if passphrase is None:
         return proto.Cancel()
      passphrase = bip39_normalize_passphrase(passphrase)
      return proto.PassphraseAck(passphrase=passphrase)

   def callback_WordRequest(self, msg):
      self.step += 1
      msg = _("Step %d/24.  Enter seed word as explained on "
               "your %s:") % (self.step, self.device)
      word = self.handler.get_word(msg)
      # Unfortunately the device can't handle self.proto.Cancel()
      return proto.WordAck(word=word)

   def callback_CharacterRequest(self, msg):
      char_info = self.handler.get_char(msg)
      if not char_info:
         return self.proto.Cancel()
      return proto.CharacterAck(**char_info)

class KeepKeyClient(GuiMixin, ProtocolMixin, BaseClient):
   def __init__(self, transport):
      BaseClient.__init__(self, transport)
      ProtocolMixin.__init__(self, transport)
      GuiMixin.__init__(self)

class DlgPinMatrix(QDialog):
   def __init__(self, lblInstruct):
      super(DlgPinMatrix, self).__init__()
      self.matrix = PinMatrixWidget()
      self.pin = ""

      self.btnAccept = QPushButton(self.tr('Accept'))
      self.btnCancel = QPushButton(self.tr("Cancel"))
      self.connect(self.btnAccept, SIGNAL(CLICKED), self.clicked)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnAccept, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)

      vbox = QVBoxLayout()
      vbox.addWidget(lblInstruct)
      vbox.addWidget(self.matrix)
      vbox.addWidget(buttonBox)
      self.setLayout(vbox)

   def clicked(self):
      self.pin = str(self.matrix.get_value())
      self.accept()

# Choose the KeepKey to setup
################################################################################
class DlgChooseKeepKey(ArmoryDialog):
   #############################################################################
   def __init__(self, parent, main):
      super(DlgChooseKeepKey, self).__init__(parent, main)
      lblDescr = QRichLabel(self.tr(
      '<b><u>Choose a KeepKey to Setup</u></b> '
      '<br><br>'
      'Use this window to setup choose which KeepKey hardware wallet '
      'to setup.'))


      lblType = QRichLabel(self.tr('<b>Available Devices:</b>'), doWrap=False)

      self.rdoBtnGrp = QButtonGroup()
      layoutRadio = QVBoxLayout()
      layoutRadio.setSpacing(0)

      transports = HidTransport.enumerate()
      self.devices = []
      id = 0
      for d in transports:
         transport = HidTransport(d)
         client = KeepKeyClient(transport)
         self.devices.append(client)
         if client.features.initialized:
            rdo = QRadioButton(self.tr("%1 [Initialized, id: %2]").arg(client.features.label,
               client.features.device_id))
         else:
            rdo = QRadioButton(self.tr("unnamed [Uninitialized, id: %1]").arg(client.features.device_id))
         self.rdoBtnGrp.addButton(rdo)
         self.rdoBtnGrp.setId(rdo, id)
         id += 1
         rdo.setChecked(True)
         layoutRadio.addWidget(rdo)

      self.rdoBtnGrp.setExclusive(True)
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

      self.setWindowTitle(self.tr('Choose a KeepKey to Setup'))

      self.setMinimumWidth(500)
      self.layout().setSizeConstraint(QLayout.SetFixedSize)

   def nextDlg(self):

      idx = self.rdoBtnGrp.checkedId()
      device = self.devices[idx]
      if device.features.initialized:
         dlg = DlgCreateKeepKeyWallet(self.parent, self.main, self.devices[idx])
      else:
         dlg = DlgSetupKeepKey(self.parent, self.main, self.devices[idx])

      self.accept()
      dlg.exec_()

# Setup the wallet for an initialized KeepKey
class DlgCreateKeepKeyWallet(ArmoryDialog):
   def __init__(self, parent, main, device):

      super(DlgCreateKeepKeyWallet, self).__init__(parent, main)
      self.device = device


# Setup an uninitialized KeepKey
class DlgSetupKeepKey(ArmoryDialog):
   def __init__(self, parent, main, device):

      super(DlgSetupKeepKey, self).__init__(parent, main)
      self.device = device
      lblDescr = QRichLabel(self.tr(
      '<b><u>An uninitialized KeepKey was selected</u></b> '
      '<br><br>'
      'Use this window to setup your KeepKey hardware wallet.'))


      lblType = QRichLabel(self.tr('<b>Options</b>'), doWrap=False)

      self.rdoBtnGrp = QButtonGroup()
      layoutRadio = QVBoxLayout()
      layoutRadio.setSpacing(0)

      self.rdoNew = QRadioButton(self.tr('Let the device generate a new seed'))
      self.rdoRecover = QRadioButton(self.tr('Recover from a BIP 39 mnemonic that you wrote down'))
      self.rdoUpload = QRadioButton(self.tr('Upload a BIP 39 mnemonic that you wrote down'))
      self.rdoUploadPK = QRadioButton(self.tr('Upload a master private key'))
      self.rdoBtnGrp.addButton(self.rdoNew)
      self.rdoBtnGrp.addButton(self.rdoRecover)
      self.rdoBtnGrp.addButton(self.rdoUpload)
      self.rdoBtnGrp.addButton(self.rdoUploadPK)
      self.rdoNew.setChecked(True)
      self.rdoBtnGrp.setExclusive(True)

      layoutRadio.addWidget(self.rdoNew)
      layoutRadio.addWidget(self.rdoRecover)
      layoutRadio.addWidget(self.rdoUpload)
      layoutRadio.addWidget(self.rdoUploadPK)

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
      layout.addWidget(lblDescr)
      layout.addWidget(lblType)
      layout.addWidget(radioButtonFrame)
      layout.addWidget(buttonBox)
      self.setLayout(layout)

      self.setWindowTitle(self.tr('Choose How to setup a KeepKey'))

      self.setMinimumWidth(500)
      self.layout().setSizeConstraint(QLayout.SetFixedSize)

   def nextDlg(self):

      if self.rdoNew.isChecked():
         dlg = DlgGenerateNew(self.parent, self.main, self.device)

      self.accept()
      dlg.exec_()

# Generate a new seed
class DlgGenerateNew(ArmoryDialog):
   def __init__(self, parent, main, device):

      super(DlgGenerateNew, self).__init__(parent, main)
      self.device = device
      lblDescr = QRichLabel(self.tr(
      '<b><u>Generate a new seed</u></b> '
      '<br><br>'
      'Use this window to setup a new KeepKey. A new seed will be generated.'))

      layoutLabel = QHBoxLayout()
      lblName = QRichLabel(self.tr('Enter a name for your device: '))
      self.edtName = QLineEdit()
      layoutLabel.addWidget(lblName)
      layoutLabel.addWidget(self.edtName)
      labelFrame = QFrame()
      labelFrame.setLayout(layoutLabel)

      self.rdoBtnGrp = QButtonGroup()
      layoutRadio = QHBoxLayout()

      self.rdo12 = QRadioButton(self.tr('12 words'))
      self.rdo18 = QRadioButton(self.tr('18 words'))
      self.rdo24 = QRadioButton(self.tr('24 words'))
      self.rdoBtnGrp.addButton(self.rdo12)
      self.rdoBtnGrp.addButton(self.rdo18)
      self.rdoBtnGrp.addButton(self.rdo24)
      self.rdo24.setChecked(True)
      self.rdoBtnGrp.setExclusive(True)

      lblWords = QRichLabel(self.tr('How long would you like your mnemonic to be?'))

      layoutRadio.addWidget(lblWords)
      layoutRadio.addWidget(self.rdo12)
      layoutRadio.addWidget(self.rdo18)
      layoutRadio.addWidget(self.rdo24)

      radioButtonFrame = QFrame()
      radioButtonFrame.setLayout(layoutRadio)

      self.chkPin = QCheckBox(self.tr('Enable PIN Protection'))
      self.chkPin.setEnabled(True)
      self.chkPassphrase = QCheckBox(self.tr('Use Passphrases'))

      self.btnAccept = QPushButton(self.tr('Next'))
      self.btnCancel = QPushButton(self.tr("Cancel"))
      self.connect(self.btnAccept, SIGNAL(CLICKED), self.nextDlg)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnAccept, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)

      layout = QVBoxLayout()
      layout.addWidget(lblDescr)
      layout.addWidget(labelFrame)
      layout.addWidget(radioButtonFrame)
      layout.addWidget(self.chkPin)
      layout.addWidget(self.chkPassphrase)
      layout.addWidget(buttonBox)
      self.setLayout(layout)

      self.setWindowTitle(self.tr('Choose How to setup a KeepKey'))

      self.setMinimumWidth(500)
      self.layout().setSizeConstraint(QLayout.SetFixedSize)

   def nextDlg(self):

      device_label = str(self.edtName.text())
      strength = 256

      if self.rdo12.isChecked():
         strength = 128
      elif self.rdo18.isChecked():
         strength = 192
      elif self.rdo24.isChecked():
         strength = 256

      use_pin = self.chkPin.isChecked()
      use_passphrase = self.chkPassphrase.isChecked()

      # Reset the device and initialize
      self.device.reset_device(True, strength, use_passphrase, use_pin,
                              device_label, 'english')

      self.accept()

# Need to put circular imports at the end of the script to avoid an import deadlock
from qtdialogs import CLICKED
