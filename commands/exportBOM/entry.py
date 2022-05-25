from openpyxl import Workbook
import adsk.core, adsk.fusion, adsk.cam, traceback
import os
import sys
sys.path.append("/usr/local/lib/python3.9/site-packages")
from .Modules import xlrd
from .Modules import xlwt

from ...lib import fusion360utils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface

# *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_BOM'
CMD_NAME = 'Export BOM'
CMD_Description = 'Export BOM of the DeepClaw Base'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the
# command it will be inserted beside. Not providing the command to position 
# it will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
COMMAND_BESIDE_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_Drawing'

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
        fileDialog.filter = 'Excel files (*.xls)'
        fileDialog.filterIndex = 0
        dialogResult = fileDialog.showSave()
        if dialogResult == adsk.core.DialogResults.DialogOK:
            config.BOM_FILE = fileDialog.filename
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
            generate_BOM(config.BASE_LENGTH, config.BASE_DEPTH, config.BASE_HEIGHT, config.BOM_FILE)
        else:
            ui.messageBox("The DeepClaw Base Model Haven't Generated!")
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def generate_BOM(length, depth, height, filename):
    try:
        workbook = xlwt.Workbook(encoding='ascii') # create a new workbook
        worksheet = workbook.add_sheet("BOM")

        # Write Input
        worksheet.write(0,0, "Component")
        worksheet.write(0,1, "Quantity")
        aluExtL = "LCF8-8080-" + str(int(length*10))
        aluExtD = "LCF8-8080-" + str(int(depth*10))
        aluExtH = "LCF8-8080-" + str(int(height*10))
        worksheet.write(1, 0, aluExtL)
        worksheet.write(1, 1, "2")
        worksheet.write(2, 0, aluExtD)
        worksheet.write(2, 1, "2")
        worksheet.write(3, 0, aluExtH)
        worksheet.write(3, 1, "4")

        worksheet.write(4, 0, "ASSF-CAP-LCE8_8080") # cap
        worksheet.write(4, 1, "4")
        worksheet.write(5, 0, "LBSB8-8080") # Cast Bracket
        worksheet.write(5, 1, "8")
        worksheet.write(6, 0, "ASSF-CONN-E8080") # Connecting Plate
        worksheet.write(6, 1, "4")
        worksheet.write(7, 0, "GD-60-F") # Wheel
        worksheet.write(7, 1, "4")
        worksheet.write(8, 0, "ASSF-RFP-UR5_AUBOi5_FrankEmika") # Robot Mounting Plate
        worksheet.write(8, 1, "1")

        workbook.save(filename)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))