from PyQt4.Qt import * #@UnusedWildImport
from PyQt4.QtGui import * #@UnusedWildImport
from qtdefines import * #@UnusedWildImport

from keepkeylib.client import KeepKeyClient
from keepkeylib.transport_hid import HidTransport

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
            rdo = QRadioButton(self.tr("unnamed [Uninitialized, id: %2").arg(client.features.label,
               client.features.device_id))
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
      layout.addWidget(layoutLabel)
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

# Restore a BIP 39 mnemonic from device
class DlgRestoreMnemonic(ArmoryDialog):
   def __init__(self, parent, main, device):

      super(DlgRestoreMnemonic, self).__init__(parent, main)
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

      self.accept()
      dlg.exec_()

# Upload a BIP 39 Mnemonic
class DlgUploadMnemonic(ArmoryDialog):
   def __init__(self, parent, main, device):

      super(DlgUploadMnemonic, self).__init__(parent, main)
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

      self.accept()
      dlg.exec_()

# Upload a master private key
class DlgUploadMPK(ArmoryDialog):
   def __init__(self, parent, main, device):

      super(DlgUploadMPK, self).__init__(parent, main)
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

      self.accept()
      dlg.exec_()

# Need to put circular imports at the end of the script to avoid an import deadlock
from qtdialogs import CLICKED
