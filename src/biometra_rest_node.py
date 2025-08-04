

"""
REST-based node that interfaces with WEI and provides various fake actions for testing purposes
"""
import clr
clr.AddReference("C:\\Users\\RPL\\source\\repos\\biometra_module\\biometra_node\\BiometraLibrary\\BiometraLibraryNet.dll")
from BiometraLibrary.ApplicationClasses.ApplicationSettingsClasses import *;
from BiometraLibrary.CommunicationClasses.NetworkClasses import *;
from BiometraLibrary.DeviceExtComClasses.BlockClasses import *;
from BiometraLibrary.DeviceExtComClasses.BlockClasses.BlockDataClasses import *;
from BiometraLibrary.DeviceExtComClasses.DeviceComClasses import *;
from BiometraLibrary.DeviceExtComClasses.LoginOutClasses import *
from BiometraLibrary.DeviceExtComClasses.LoginOutClasses.UserClasses.UserDataClasses import *;
from BiometraLibrary.DeviceExtComClasses.ProgClasses import *;
from  BiometraLibrary.DeviceExtComClasses.ProgClasses.ProgDataClasses import *;
from BiometraLibrary.DeviceExtComClasses.ProgClasses.ProgDataClasses.ProgEditClasses import *;
from BiometraLibrary.DeviceExtComClasses.SystemClasses.InfoClasses import *;
import BiometraLibrary.DeviceExtComClasses.SystemClasses.InfoClasses.InfoDataClasses;
from BiometraLibrary.DeviceExtComClasses.SystemClasses.TcdaClasses import *;
from BiometraLibrary.HelperClasses.CheckStateHelperClasses import *;
import BiometraLibrary.HelperClasses.DataSetHelperClasses;
import BiometraLibrary.HelperClasses.ListHelperClasses;
import BiometraLibrary.HelperClasses.UnitHelperClasses;
import time
import glob
import os


from typing import Annotated

from fastapi.datastructures import State
from wei.modules.rest_module import RESTModule
from wei.types import StepResponse
from wei.types.step_types import StepSucceeded, StepFailed
from wei.types.module_types import (
    ModuleState,
)
from wei.types.step_types import ActionRequest

# * Test predefined action functions


biometra_rest_node = RESTModule(
    name="biometra_node",
    description="A module to control the Biometra thermocycler",
    version="1.0.0",
    resource_pools=[],
    model="Biometra",
    actions=[],
)



biometra_rest_node.arg_parser.add_argument(
    "--device",
    type=str,
    default="biometra3",
    help="name for communicating with the device",
)


@biometra_rest_node.startup()
def test_node_startup(state: State):
    """Initializes the module"""
    ApplicationSettings.LoadApplicationSettings()
    ApplicationSettings.CommunicationSettings.SerialComSettings.SerialComParams = BiometraLibrary.CommunicationClasses.SerialComClasses.SerialParams(BiometraLibrary.CommunicationClasses.SerialComClasses.EnBaudRate.BAUDRATE_115200, BiometraLibrary.CommunicationClasses.SerialComClasses.EnParity.PARITY_NONE, BiometraLibrary.CommunicationClasses.SerialComClasses.EnDataBits.DATABITS_8, BiometraLibrary.CommunicationClasses.SerialComClasses.EnStopBits.STOPBITS_ONE, BiometraLibrary.CommunicationClasses.EnCommunicationTimeout.TIMEOUT_1500ms)
    ApplicationSettings.CommunicationSettings.SerialComSettings.AllComPorts = True
    ApplicationSettings.CommunicationSettings.SerialComSettings.EnableCommunication = True;
    test = InfoCmds.GetAllComAvailableDevices()
    for device in list(test[1].DataList):
        if str(device.DeviceInfos.DeviceDescriptionInfo) == state.device:
            state.device = device.DeviceInfos.DeviceDescriptionInfo
    print(list(test[1].DataList))
    print(list(test[1].DataList)[0])
    print(list(test[1].DataList)[0].DeviceInfos.DeviceDescriptionInfo)
    device = list(test[1].DataList)[0].DeviceInfos.DeviceDescriptionInfo
    print(DeviceCom.GetNumberOfScannedDevices())
    blockCmds = BlockCmds(ApplicationSettings.CommunicationSettings, device)
    print(state.device)

@biometra_rest_node.state_handler()
def state_handler(state: State) -> ModuleState:
    """Handles the state of the module"""
    tcdaCmds = TcdaCmds(ApplicationSettings.CommunicationSettings, state.device,)
    deviceComResult, test = tcdaCmds.GetBlockState(state.device, BlockNumber(1),  BlockState())
    if test.ActiveBlock:
        return ModuleState(status=state.status)
    else:
        return ModuleState(status=state.status)

@biometra_rest_node.action(
    name="open",
    description="Opens the Biometra Lid",
)
def open(state: State, action: ActionRequest) -> StepResponse:
    """
    opens the Biometra Lid
    """
    start = time.time()
    while time.time() - start < 60:
        if get_lid_state(state.device) == "closed":
            blockCmds = BlockCmds(ApplicationSettings.CommunicationSettings, state.device)
            blockCmds.OpenMotLid(state.device, BlockNumber(1))
            command_sent = time.time()
            while time.time() - command_sent < 60:
                if get_lid_state(state.device) == "open":
                    return StepSucceeded()
                time.sleep(1)
            else:
                return StepFailed(error="Timeout after sending command")
        if get_lid_state(state.device) == "open":
            return StepSucceeded()
        time.sleep(1)
    else:
        return StepFailed(error="Timeout waiting for lid state")
    

@biometra_rest_node.action(
    name="close",
    description="Closes the Biometra Lid",
)
def close(state: State, action: ActionRequest) -> StepResponse:
    """
    closes the Biometra Lid
    """
    start = time.time()
    while time.time() - start < 60:
        if get_lid_state(state.device) == "open":
            blockCmds = BlockCmds(ApplicationSettings.CommunicationSettings, state.device)
            blockCmds.CloseMotLid(state.device, BlockNumber(1))
            command_sent = time.time()
            while time.time() - command_sent < 60:
                if get_lid_state(state.device) == "closed":
                    return StepSucceeded()
                time.sleep(1)
            else:
                return StepFailed(error="Timeout after sending command")
        if get_lid_state(state.device) == "closed":
            return StepSucceeded()
        time.sleep(1)
    else:
        return StepFailed(error="Timeout waiting for lid state")



@biometra_rest_node.action(
    name="run_program",
    description="Runs a program on the Biometra",
)
def run_program(state: State, action: ActionRequest,  program_number: Annotated[int, "program to run"]) -> StepResponse:
    """
    runs a program on the biometra
    """
    blockCmds = BlockCmds(ApplicationSettings.CommunicationSettings, state.device)
    checkStateResult = blockCmds.StartProgramOnBlock(state.device, UserInitials("ADM"), ProgramNumber(program_number, EnProgramType.TYPE_PROGRAM), BlockNumber(1), True)
    

    tcdaCmds = TcdaCmds(ApplicationSettings.CommunicationSettings, state.device,)
    deviceComResult, test = tcdaCmds.GetBlockState(state.device, BlockNumber(1),  BlockState())
    while(not(test.ActiveBlock)):
        
        tcdaCmds = TcdaCmds(ApplicationSettings.CommunicationSettings, state.device,)
        deviceComResult, test = tcdaCmds.GetBlockState(state.device, BlockNumber(1),  BlockState())
    await_not_busy(state.device)
    while(get_lid_state(state.device) == "busy"):
        print("waiting")
        time.sleep(1)
    return StepSucceeded()


def await_not_busy(device: any):
    tcdaCmds = TcdaCmds(ApplicationSettings.CommunicationSettings, device,)
    deviceComResult, response = tcdaCmds.GetBlockState(device, BlockNumber(1),  BlockState())
    print(deviceComResult, response.ActiveBlock)
    while(response.ActiveBlock):
        tcdaCmds = TcdaCmds(ApplicationSettings.CommunicationSettings, device,)
        deviceComResult, response = tcdaCmds.GetBlockState(device, BlockNumber(1),  BlockState())

def get_lid_state(device: any):
            tcdaCmds = TcdaCmds(ApplicationSettings.CommunicationSettings, device)
            deviceComResult, response = tcdaCmds.GetMotLidState(device)
            print("getting lid state...")
            lid_state = response.ToString()
            print(response)
            if lid_state == "0000 0000 0000 0011;;":
                return "open"
            elif lid_state == "0000 0000 0000 0101;;":
                return "closed"
            
            else:
                return "busy"







if __name__ == "__main__":
    biometra_rest_node.start()


