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

# Need to put circular imports at the end of the script to avoid an import deadlock
from qtdialogs import CLICKED