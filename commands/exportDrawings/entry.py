import adsk.core, adsk.fusion, adsk.cam, traceback
import os

import sys
sys.path.append("/usr/local/lib/python3.9/site-packages")

# from .Modules.PyPDF2 import PdfFileWriter, PdfFileReader
# import io
# from .Modules.reportlab.pdfgen import canvas
# from .Modules.reportlab.lib.pagesizes import A3, landscape

from PyPDF2 import PdfFileWriter, PdfFileReader
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape

from ...lib import fusion360utils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface

# *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_Drawing'
CMD_NAME = 'Export Drawings'
CMD_Description = 'Export Enginneering Drawings of the DeepClaw Base'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the
# command it will be inserted beside. Not providing the command to position 
# it will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
COMMAND_BESIDE_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_Pedestal'

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

# Executed when add-in is run.
def start():
    try:
        # Create a command Definition.
        cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

        # Define an event handler for the command created event.
        # It will be called when button is clicked.
        futil.add_handler(cmd_def.commandCreated, command_created)
        
        # **** Add a button into the UI so the user can run the command. ****
        # Get the target workspace the button will be created in.
        workspace = ui.workspaces.itemById(WORKSPACE_ID)

        # Get the panel the button will be created in.
        panel = workspace.toolbarPanels.itemById(PANEL_ID)

        # Create the button command control in the UI after the specified existing command.
        control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)

        # Specify if the command is promoted to the main toolbar
        control.isPromoted = IS_PROMOTED
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# Executed when add-in is stopped
def stop():
    try:
        # Get the various UI elements for this command
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
        command_control = panel.controls.itemById(CMD_ID)
        command_definition = ui.commandDefinitions.itemById(CMD_ID)

        # Delete the button command control
        if command_control:
            command_control.deleteMe()

        # Delete the command definition
        if command_definition:
            command_definition.deleteMe()
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def command_created(args: adsk.core.CommandCreatedEventArgs):
    try:
        # General logging for debug
        futil.log(f'{CMD_NAME} Command Creted Event')

        # Ask user input the output file name
        fileDialog = ui.createFileDialog()
        fileDialog.isMultiSelectEnabled = False
        fileDialog.title = "Specify result filename"
        fileDialog.filter = 'PDF files (*.pdf)'
        fileDialog.filterIndex = 0
        dialogResult = fileDialog.showSave()
        if dialogResult == adsk.core.DialogResults.DialogOK:
            config.DRAWING_NAME = fileDialog.filename
        else:
            return

        

        # Connect to the events that are need by this command.
        futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def command_execute(args: adsk.core.CommandEventArgs):
    try:
        eventArgs = adsk.core.CommandEventArgs.cast(args)

        if config.IS_DCBASE_GENERATE:
            generate_drawing(config.BASE_LENGTH, config.BASE_DEPTH, config.BASE_HEIGHT, config.DRAWING_NAME)
        else:
            ui.messageBox("The DeepClaw Base Model Haven't Generated!")
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def generate_drawing(length, depth, height, filename):
    try:
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=landscape(A3))
        width, height = A3
        # can.drawString(900, 660, "Length = xxx mm")
        # can.drawString(900, 630, "Width = xxx mm")
        # can.drawString(900, 600, "Height = xxx mm")
        lString = "Length = " + str(config.BASE_LENGTH*10) + " mm"
        dString = "Width = " + str(config.BASE_DEPTH*10) + " mm"
        hString = "Height = " + str(config.BASE_HEIGHT*10) + " mm"
        can.drawString(900, 660, lString)
        can.drawString(900, 630, dString)
        can.drawString(900, 600, hString)
        can.save()

        #move to the beginning of the StringIO buffer
        packet.seek(0)

        # create a new PDF with Reportlab
        new_pdf = PdfFileReader(packet)
        # read your existing PDF
        fileName = os.path.join(os.path.abspath(os.path.dirname(__file__)), './Drawing.pdf')
        # existing_pdf = PdfFileReader(open("./DCBase_Drawing.pdf", "rb"), strict=False) # The default size of the drawing is A3
        existing_pdf = PdfFileReader(open(fileName, "rb"), strict=False)
        output = PdfFileWriter()
        # add the "watermark" (which is the new pdf) on the existing page
        page = existing_pdf.getPage(0)
        page.mergePage(new_pdf.getPage(0))
        output.addPage(page)
        # finally, write "output" to a real file
        outputStream = open(filename, "wb")
        output.write(outputStream)
        outputStream.close()
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


            


