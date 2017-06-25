from btchip.btchip import btchip
from btchip.btchipComm import HIDDongleHIDAPI
from btchip.btchipPersoWizard import StartBTChipPersoDialog

from PyQt4.Qt import * #@UnusedWildImport
from PyQt4.QtGui import * #@UnusedWildImport
from qtdefines import * #@UnusedWildImport

import hid

# Choose the Ledger to setup
################################################################################
class DlgChooseLedger(ArmoryDialog):
   #############################################################################
   def __init__(self, parent, main):
      super(DlgChooseLedger, self).__init__(parent, main)

      lblDescr = QRichLabel(self.tr(
      '<b><u>Choose a Ledger Nano S to Setup</u></b> '
      '<br><br>'
      'Use this window to setup choose which Ledger Nano S hardware wallet '
      'to setup.'))


      lblType = QRichLabel(self.tr('<b>Available Devices:</b>'), doWrap=False)

      self.rdoBtnGrp = QButtonGroup()
      layoutRadio = QVBoxLayout()
      layoutRadio.setSpacing(0) 

      self.devices = []
      id = 0
      for hidDevice in hid.enumerate(0, 0):
         if hidDevice['vendor_id'] == 0x2c97: # Ledger Nano S
            dev = hid.device()
            dev.open_path(hidDevice['path'])
            dev.set_nonblocking(True)
            dongle = HIDDongleHIDAPI(dev, True, False)
            client = btchip(dongle)
            self.devices.append(client)
            rdo = QRadioButton(self.tr("Ledger Device "))
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

      self.setWindowTitle(self.tr('Choose a Ledger to Setup'))

      self.setMinimumWidth(500)
      self.layout().setSizeConstraint(QLayout.SetFixedSize)

   def nextDlg(self):
      idx = self.rdoBtnGrp.checkedId()
      device = self.devices[idx]
      dlg = DlgCreateLedgerWallet(self.parent, self.main, self.devices[idx])

      self.accept()
      dlg.exec_()

# Setup the wallet for an initialized Ledger
class DlgCreateLedgerWallet(ArmoryDialog):
   def __init__(self, parent, main, device):
      super(DlgCreateLedgerWallet, self).__init__(parent, main)
      self.device = device

# Need to put circular imports at the end of the script to avoid an import deadlock
from qtdialogs import CLICKED