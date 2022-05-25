
import adsk.core, adsk.fusion, adsk.cam, traceback
import os
import math

from ...lib import fusion360utils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface

# *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_Pedestal'
CMD_NAME = 'Build Pedestal'
CMD_Description = 'A Fusion 360 Add-in Command to Build a Reconfigable DeepClaw Pedestal'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the
# command it will be inserted beside. Not providing the command to position 
# it will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

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
        # General logging for debug.
        futil.log(f'{CMD_NAME} Command Created Event')

        # Create inputs
        inputs = args.command.commandInputs

        # Create the value input to get the depth
        depth = inputs.addValueInput('depthValue', 'Depth Value', 'cm', adsk.core.ValueInput.createByReal(0))
        # Create the value input to get the length
        length = inputs.addValueInput('lengthValue', 'Length Value', 'cm', adsk.core.ValueInput.createByReal(0))
        # Create the value input to get the height
        height = inputs.addValueInput('heightValue', 'Height Value', 'cm', adsk.core.ValueInput.createByReal(0))

        # Connect to the events that are needed by this command.
        futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def command_execute(args: adsk.core.CommandEventArgs):
    try:
        eventArgs = adsk.core.CommandEventArgs.cast(args)

        # Code to react to the event.
        # app = adsk.core.Application.get()
        # ui = app.userInterface
        des = adsk.fusion.Design.cast(app.activeProduct)

        # Get the values from the command inputs
        inputs = eventArgs.command.commandInputs
        depth = inputs.itemById('depthValue').value
        length = inputs.itemById('lengthValue').value
        height = inputs.itemById('heightValue').value

        # Store the parameter values of the DCBase to constants
        config.BASE_DEPTH = float(depth)
        config.BASE_LENGTH = float(length)
        config.BASE_HEIGHT = float(height)

        generateBase(depth, length, height)
        config.IS_DCBASE_GENERATE = True

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def profile_with_most_loops(sketch: adsk.fusion.Sketch, component: adsk.fusion.Component):
    "get the profile with the most inner loops"
    
    if sketch.profiles.count == 0:
        return
    else:
        # start with the first profile
        the_profile = sketch.profiles.item(0)
        the_profile_loop_count = the_profile.profileLoops.count
        # find the profile with the most loops
        if sketch.profiles.count > 1:
            for i in range(1, sketch.profiles.count):
                next_profile = sketch.profiles.item(i)
                next_profile_loop_count = next_profile.profileLoops.count
                if next_profile_loop_count > the_profile_loop_count:
                    the_profile = next_profile
                    the_profile_loop_count = next_profile_loop_count

        return the_profile

# Creat a extrusion by length with the default LCF8-8080 profile
def createExtrusion(importManager, distance, comp, consPlane):
    # get .dxf file directory
    fileName = os.path.join(os.path.abspath(os.path.dirname(__file__)), './importFiles/LCF8-8080.dxf')

    # Get dxf import options
    dxfOptions = importManager.createDXF2DImportOptions(fileName, consPlane)
    dxfOptions.isViewFit = True
    dxfOptions.isSingleSketchResult = True

    # Import dxf file to rootComponent
    importManager.importToTarget(dxfOptions, comp)

    # Get reference to the sketches
    sketches = comp.sketches

    # Get the sketch from sketches
    sketch = sketches.item(0)

    # Get profile from sketch for extrusion
    profile_ext = profile_with_most_loops(sketch, comp)
    # profile_ext = outer_loops(sketch)

    # create an extrusion input
    extrudes = comp.features.extrudeFeatures # create a extrusion in component1
    operation_type = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    ext_input = extrudes.createInput(profile_ext, operation_type)

    # Set the distance extent to be single direction
    ext_input.setDistanceExtent(False, distance)

    # Set the extrude to be a solid one
    ext_input.isSolid = True

    # Create the extrusion
    return extrudes.add(ext_input)

def rotBySelf(occurrence, angle, axis):
    "Rotate by self coordinate system"
    origin = adsk.core.Point3D.create() # to store the origine point of the occurrence's coordinate system
    xAxis = adsk.core.Vector3D.create() # to store the xAxis of the occurrence's coordinate system
    yAxis = adsk.core.Vector3D.create() # to store the yAxis of the occurrence's coordiante system
    zAxis = adsk.core.Vector3D.create() # to store the zAxis of the occurrence's coordiante system 
    (origin, xAxis, yAxis, zAxis) = occurrence.transform.getAsCoordinateSystem() # get the occurrence's coordinate system
    
    if axis == 'x':
        rotAxis = xAxis
    elif axis == 'y':
        rotAxis = yAxis
    elif axis == 'z':
        rotAxis = zAxis
    
    rot = adsk.core.Matrix3D.create()
    rot.setToRotation(angle, rotAxis, origin)
    trans = occurrence.transform
    trans.transformBy(rot)
    occurrence.transform = trans

def translation(occurrence, distance, axis):
    "Translation by the world coordination"
    trans = adsk.core.Matrix3D.create()

    if axis == 'x':
        trans.translation = adsk.core.Vector3D.create(distance, 0, 0)
    elif axis == 'y':
        trans.translation = adsk.core.Vector3D.create(0.0, distance, 0.0)
    elif axis == 'z':
        trans.translation = adsk.core.Vector3D.create(0.0, 0.0, distance)
    
    transform = occurrence.transform
    transform.transformBy(trans)
    occurrence.transform = transform

def generateBase(depth, length, height):
    # TODO: try to using joint to assembly all the comments

    ui = None
    try:
        app = adsk.core.Application.get() # the root from the Fusion 360 API Object Model
        ui  = app.userInterface

        # transfer into valueInput
        l = float(length)
        h = float(height)
        d = float(depth)
        length = adsk.core.ValueInput.createByReal(float(length))
        height = adsk.core.ValueInput.createByReal(float(height))
        depth = adsk.core.ValueInput.createByReal(float(depth))

        # Get import manager
        importManager = app.importManager

        design = app.activeProduct # Every file in fusion is a design

        # Get reference to the root component
        rootComp = design.rootComponent

        # Create a new occurrence to create an associated component to create the first depth extrusion
        trans1 = adsk.core.Matrix3D.create()
        occDep1 = rootComp.occurrences.addNewComponent(trans1)
        depth_comp = occDep1.component
        depth_comp.name = "LCF8-8080-depth: " + str(d) + " cm"
        ext_depth = createExtrusion(importManager, depth, depth_comp, depth_comp.xZConstructionPlane) # create an extrusion in depth direction

        # Add the second depth extrusion occurrence from the depth component
        trans2 = adsk.core.Matrix3D.create()
        trans2.translation = adsk.core.Vector3D.create(l+8, 0.0, 0.0)
        occDep2 = rootComp.occurrences.addExistingComponent(depth_comp, trans2)

        # Create occurrence for length extrusion which comes from the length component
        trans3 = adsk.core.Matrix3D.create()
        trans3.translation = adsk.core.Vector3D.create(4.0, d/2-6, 0.0)
        occLen1 = rootComp.occurrences.addNewComponent(trans3)
        length_comp = occLen1.component
        length_comp.name = "LCF8-8080-length: " + str(l) + " cm"
        ext_length = createExtrusion(importManager, length, length_comp, length_comp.yZConstructionPlane)

        # Add the second depth extrusion occurrence from the length component
        trans4 = adsk.core.Matrix3D.create()
        trans4.translation = adsk.core.Vector3D.create(0.0, 12.0, 0.0)
        occLen2 = rootComp.occurrences.addExistingComponent(length_comp, trans4)

        # Create occurrence for height extrusion
        trans5 = adsk.core.Matrix3D.create()
        trans5.translation = adsk.core.Vector3D.create(l/2 - 2.0, d/2 - 6.0, 4.0)
        occHei1 = rootComp.occurrences.addNewComponent(trans5)
        height_comp = occHei1.component
        height_comp.name = "LCF8-8080-height: " + str(h) + " cm"
        ext_height = createExtrusion(importManager, height, height_comp, height_comp.xYConstructionPlane)

        # Add the second height extrusion occurrence from the height component
        trans6 = adsk.core.Matrix3D.create()
        trans6.translation = adsk.core.Vector3D.create(12.0, 0, 0)
        occHei2 = rootComp.occurrences.addExistingComponent(height_comp, trans6)

        # Add the third height extrusion occurrence from the height component
        trans7 = adsk.core.Matrix3D.create()
        trans7.translation = adsk.core.Vector3D.create(12.0, 12.0, 0)
        occHei3 = rootComp.occurrences.addExistingComponent(height_comp, trans7)

        # Add the fourth height extrusion occurrence from the height component
        trans8 = adsk.core.Matrix3D.create()
        trans8.translation = adsk.core.Vector3D.create(0.0, 12.0, 0)
        occHei4 = rootComp.occurrences.addExistingComponent(height_comp, trans8)

        ## setup all the caps
        # import cap step file
        capFileName = os.path.join(os.path.abspath(os.path.dirname(__file__)), "./importFiles/ASSF-CAP-LCEC8_8080_B.step")
        capStepImpOpt = importManager.createSTEPImportOptions(capFileName)
        importManager.importToTarget(capStepImpOpt, rootComp)
        
        occCap1 = rootComp.occurrences.item(8) # refers to the Cap occurrances
        capComp = occCap1.component # get the associated component of the cap

        # set up the first cap
        rotBySelf(occCap1, -math.pi/2, 'x')
        translation(occCap1, -0.4, 'y')

        # set up the second cap
        transCap2 = adsk.core.Matrix3D.create()
        transCap2.translation = adsk.core.Vector3D.create(l+8, 0.0, 0.0)
        occCap2 = rootComp.occurrences.addExistingComponent(capComp, transCap2) # create a new occurrence for the cap component

        # set up the third cap
        transCap3 = adsk.core.Matrix3D.create()
        transCap3.translation = adsk.core.Vector3D.create(0.0, d+0.8, 0.0)
        occCap3 = rootComp.occurrences.addExistingComponent(capComp, transCap3)
        rotBySelf(occCap3, math.pi, 'y')

        # set up the fourth cap
        transCap4 = adsk.core.Matrix3D.create()
        transCap4.translation = adsk.core.Vector3D.create(l+8, d+0.8, 0.0)
        occCap4 = rootComp.occurrences.addExistingComponent(capComp, transCap4)
        rotBySelf(occCap4, math.pi, 'y')

        ## set up all the wheel connectors(140*80*20 mm)
        # import wheel connector STEP file
        wheelConFileName = os.path.join(os.path.abspath(os.path.dirname(__file__)), "./importFiles/ASSF-CONN-E8080.step")
        wheelConStepImpOpt = importManager.createSTEPImportOptions(wheelConFileName)
        importManager.importToTarget(wheelConStepImpOpt, rootComp)

        occWheelCon1 = rootComp.occurrences.item(12)
        wheelConComp = occWheelCon1.component

        # set up the first wheel connnceter
        translation(occWheelCon1, -4.0, 'z')
        translation(occWheelCon1, 7.0, 'y')
        rotBySelf(occWheelCon1, -math.pi/2, 'x')
        rotBySelf(occWheelCon1, math.pi/2, 'y')

        # set up the second wheel connector
        transWheelCon2 = adsk.core.Matrix3D.create()
        transWheelCon2.translation = adsk.core.Vector3D.create(l+8, 0.0, 0.0)
        occWheelCon2 = rootComp.occurrences.addExistingComponent(wheelConComp, transWheelCon2)

        # set up the third wheel connector
        transWheelCon3 = adsk.core.Matrix3D.create()
        transWheelCon3.translation = adsk.core.Vector3D.create(l+8, d-14, 0.0)
        occWheelCon3 = rootComp.occurrences.addExistingComponent(wheelConComp, transWheelCon3)

        # set up the fourth conncetor
        transWheelCon4 = adsk.core.Matrix3D.create()
        transWheelCon4.translation = adsk.core.Vector3D.create(0.0, d-14, 0.0)
        occWheelCon4 = rootComp.occurrences.addExistingComponent(wheelConComp, transWheelCon4)

        ## Set up all the wheels
        # import wheel step file
        wheelFileName = os.path.join(os.path.abspath(os.path.dirname(__file__)), "./importFiles/GD-60-F.step")
        wheelStepImpOpt = importManager.createSTEPImportOptions(wheelFileName)
        importManager.importToTarget(wheelStepImpOpt, rootComp)        

        occWheel1 = rootComp.occurrences.item(16)
        wheelComp = occWheel1.component

        # set up the first wheel  
        translation(occWheel1, -7.33, 'z')
        translation(occWheel1, 7.0, 'y')
        rotBySelf(occWheel1, -math.pi/2, 'z')

        # set up the second wheel
        transWheel2 = adsk.core.Matrix3D.create()
        transWheel2.translation = adsk.core.Vector3D.create(l+8, 0.0, 0.0)
        occWheel2 = rootComp.occurrences.addExistingComponent(wheelComp, transWheel2)

        # set up the third wheel
        transWheel3 = adsk.core.Matrix3D.create()
        transWheel3.translation = adsk.core.Vector3D.create(l+8, d-14, 0.0)
        occWheel3 = rootComp.occurrences.addExistingComponent(wheelComp, transWheel3)     

        # set up the fourth wheel
        transWheel4 = adsk.core.Matrix3D.create()
        transWheel4.translation = adsk.core.Vector3D.create(0.0, d-14, 0.0)
        occWheel4 = rootComp.occurrences.addExistingComponent(wheelComp, transWheel4)

        ## set up all the extrusions connectors
        # import the extrusion connector step file
        extConFileName = os.path.join(os.path.abspath(os.path.dirname(__file__)), "./importFiles/LBSB8-8080.step")
        extConStepImpOpt = importManager.createSTEPImportOptions(extConFileName)
        importManager.importToTarget(extConStepImpOpt, rootComp)

        occExtCon1 = rootComp.occurrences.item(20)
        extConComp = occExtCon1.component

        # # set up the first extrusion conncetor
        rotBySelf(occExtCon1, math.pi/2, 'x')
        translation(occExtCon1, 4.0, 'x')
        translation(occExtCon1, d/2 - 10, 'y')

        # set up the second extrusion connector
        transExtCon2 = adsk.core.Matrix3D.create()
        transExtCon2.translation = adsk.core.Vector3D.create(l, 0.0, 0.0)
        occExtCon2 = rootComp.occurrences.addExistingComponent(extConComp, transExtCon2)
        rotBySelf(occExtCon2, -math.pi/2, 'y')

        # set up the third extrusion connector
        transExtCon3 = adsk.core.Matrix3D.create()
        transExtCon3.translation = adsk.core.Vector3D.create(l, 20, 0.0)
        occExtCon3 = rootComp.occurrences.addExistingComponent(extConComp, transExtCon3)
        rotBySelf(occExtCon3, -math.pi, 'y')    

        # set up the fourth extrusion connector
        transExtCon4 = adsk.core.Matrix3D.create()
        transExtCon4.translation = adsk.core.Vector3D.create(0.0, 20, 0.0)
        occExtCon4 = rootComp.occurrences.addExistingComponent(extConComp, transExtCon4)   
        rotBySelf(occExtCon4, math.pi/2, 'y')      

        # set up the fifth extrusion connector
        transExtCon5 = adsk.core.Matrix3D.create()
        transExtCon5.translation = adsk.core.Vector3D.create(l/2 - 10, 4, 4)
        occExtCon5 = rootComp.occurrences.addExistingComponent(extConComp, transExtCon5)
        rotBySelf(occExtCon5, -math.pi/2, 'x')
        rotBySelf(occExtCon5, math.pi, 'z')

        # set up the sixth extrusion connector
        transExtCon6 = adsk.core.Matrix3D.create()
        transExtCon6.translation = adsk.core.Vector3D.create(l/2 + 10, 4, 4)
        occExtCon6 = rootComp.occurrences.addExistingComponent(extConComp, transExtCon6)
        rotBySelf(occExtCon6, -math.pi/2, 'x')   

        # set up seventh extrusion connector
        transExtCon7 = adsk.core.Matrix3D.create()
        transExtCon7.translation = adsk.core.Vector3D.create(l/2 - 10, 16, 4)
        occExtCon7 = rootComp.occurrences.addExistingComponent(extConComp, transExtCon7)
        rotBySelf(occExtCon7, -math.pi/2, 'x')
        rotBySelf(occExtCon7, math.pi, 'z')  

        # set up the eighth extrusion connector
        transExtCon8 = adsk.core.Matrix3D.create()
        transExtCon8.translation = adsk.core.Vector3D.create(l/2 + 10, 16, 4)
        occExtCon8 = rootComp.occurrences.addExistingComponent(extConComp, transExtCon8) 
        rotBySelf(occExtCon8, -math.pi/2, 'x')   


        ## set up the flange
        flangeFileName = os.path.join(os.path.abspath(os.path.dirname(__file__)), "./importFiles/ASSF-RFP-UR5_AUBOi5_FrankEmika-200_200_20.step")
        flangeStepImpOpt = importManager.createSTEPImportOptions(flangeFileName)
        importManager.importToTarget(flangeStepImpOpt, rootComp)

        occFlange = rootComp.occurrences.item(28)
        flangeComp = occFlange.component

        rotBySelf(occFlange, math.pi/2, 'x')
        translation(occFlange, l/2 + 4, 'x')
        translation(occFlange, d/2, 'y')
        translation(occFlange, h+4, 'z')

        # # Create the AsBuiltJoint
        # asBuiltJoints = rootComp.asBuiltJoints
        # asBuiltJointInput = asBuiltJoints.createInput(occDep1, occLen1, None)
        # asBuiltJoints.add(asBuiltJointInput)

        # return True

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

