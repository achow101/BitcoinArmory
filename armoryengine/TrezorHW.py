from PyQt4.Qt import * #@UnusedWildImport
from PyQt4.QtGui import * #@UnusedWildImport
from qtdefines import * #@UnusedWildImport

from trezorlib.client import TrezorClient
from trezorlib.transport_hid import HidTransport

# Choose the trezor to setup
################################################################################
class DlgChooseTrezor(ArmoryDialog):
   #############################################################################
   def __init__(self, parent, main):
      super(DlgChooseTrezor, self).__init__(parent, main)

      lblDescr = QRichLabel(self.tr(
      '<b><u>Choose a Trezor to Setup</u></b> '
      '<br><br>'
      'Use this window to setup choose which Trezor hardware wallet '
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
         client = TrezorClient(transport)
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

      self.setWindowTitle(self.tr('Choose a Trezor to Setup'))

      self.setMinimumWidth(500)
      self.layout().setSizeConstraint(QLayout.SetFixedSize)

   def nextDlg(self):

      idx = self.rdoBtnGrp.checkedId()
      device = self.devices[idx]
      if device.features.initialized:
         dlg = DlgCreateTrezorWallet(self.parent, self.main, self.devices[idx])
      else:
         dlg = DlgSetupTrezor(self.parent, self.main, self.devices[idx])

      self.accept()
      dlg.exec_()

# Setup the wallet for an initialized trezor
class DlgCreateTrezorWallet(ArmoryDialog):
   def __init__(self, parent, main, device):

      super(DlgCreateTrezorWallet, self).__init__(parent, main)
      self.device = device


# Setup an uninitialized Trezor
class DlgSetupTrezor(ArmoryDialog):
   def __init__(self, parent, main, device):

      super(DlgSetupTrezor, self).__init__(parent, main)
      self.device = device

# Need to put circular imports at the end of the script to avoid an import deadlock
from qtdialogs import CLICKED