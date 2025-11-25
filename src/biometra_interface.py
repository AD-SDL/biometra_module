"""Interface for controlling the Biometra thermocycler via pythonnet."""

import gc
import time
from typing import Optional

from madsci.client.event_client import EventClient

import clr

# clr.AddReference
clr.AddReference("C://Users//RPL//source//repos//biometra_module//src//BiometraLibrary//BiometraLibraryNet.dll") #TODO: fix path

from BiometraLibrary.ApplicationClasses.ApplicationSettingsClasses import (
    ApplicationSettings,
)
from BiometraLibrary.CommunicationClasses.SerialComClasses import (
    EnBaudRate,
    EnDataBits,
    EnParity,
    EnStopBits,
    SerialParams,
)
from BiometraLibrary.CommunicationClasses import EnCommunicationTimeout
from BiometraLibrary.DeviceExtComClasses.BlockClasses import BlockCmds
from BiometraLibrary.DeviceExtComClasses.BlockClasses.BlockDataClasses import BlockNumber
from BiometraLibrary.DeviceExtComClasses.DeviceComClasses import DeviceCom, DeviceComParams
from BiometraLibrary.DeviceExtComClasses.LoginOutClasses import LoginOutCmds
from BiometraLibrary.DeviceExtComClasses.LoginOutClasses.UserClasses.UserDataClasses import (
    UserInitials,
    UserPassword,
)
from BiometraLibrary.DeviceExtComClasses.ProgClasses.ProgDataClasses.ProgEditClasses import ProgramNumber, EnProgramType
# from BiometraLibrary.DeviceExtComClasses.ProgClasses import EnProgramType
from BiometraLibrary.DeviceExtComClasses.SystemClasses.InfoClasses import InfoCmds
from BiometraLibrary.DeviceExtComClasses.SystemClasses.TcdaClasses import TcdaCmds
from System import GC


class BiometraInterface:
    """Interface for the Biometra thermocycler via BiometraLibrary."""

    def __init__(
        self,
        logger: EventClient = None,
    ) -> None:
        """Initialize the Biometra interface"""
        self.device_list = None
        self.connected_device_num = None
        self.logger = logger or EventClient()
        self._initialize_connection()
    

    def _initialize_connection(self) -> None:
        """Initialize serial connection and find devices."""
        try:
            ApplicationSettings.LoadApplicationSettings()

            # configure serial communication
            ApplicationSettings.CommunicationSettings.SerialComSettings.SerialComParams = SerialParams(
                EnBaudRate.BAUDRATE_115200,
                EnParity.PARITY_NONE,
                EnDataBits.DATABITS_8,
                EnStopBits.STOPBITS_ONE,
                EnCommunicationTimeout.TIMEOUT_1500ms,
            )

            ApplicationSettings.CommunicationSettings.SerialComSettings.AllComPorts = True

            # Enable serial communication
            ApplicationSettings.CommunicationSettings.SerialComSettings.EnableCommunication = True

            ApplicationSettings.SaveApplicationSettings()
            self.logger.log_info("Serial connection enabled")
            print("serial connection enabled")

            # Get device list

            devices = InfoCmds.GetAllComAvailableDevices()
            print(devices)
            self.device_list = DeviceCom.GetSavedDeviceDescriptions()
            self.logger.log(f"Found {self.device_list.Count} Biometra device(s)")

        except Exception as e:
            self.logger.log_error(f"Failed to initialize Biometra connection: {e}")
            raise

    def connect_device(self, plate_type: int) -> int:
        """Connect to a device that matches the plate type.

        Args:
            plate_type: Plate type (96 or 384)

        Returns:
            Device number that was connected
        """
        device_num = self._find_device(plate_type)
        if device_num < 0:
            raise ValueError(f"No device found for plate type {plate_type}")

        self.connected_device_num = device_num
        self._login_user(device_num)
        self.logger.log(f"Connected to device {device_num} for plate type {plate_type}")
        return device_num

    def _find_device(self, plate_type: int) -> int:
        """Find a device that fits the plate type.

        Args:
            plate_type: Plate type (96 or 384)

        Returns:
            Device number or -1 if not found
        """
        for i in range(self.device_list.Count):
            block_type = self._get_block_type(i)
            if block_type == plate_type:
                return i

        self.logger.log_error(f"No device with plate type {plate_type} found")
        return -1

    def _get_block_type(self, device_num: int) -> int:
        """Get the block type for a device.

        Args:
            device_num: Device index

        Returns:
            Block type (96 or 384) or -1 on error
        """
        info_cmds = InfoCmds(
            ApplicationSettings.CommunicationSettings, self.device_list[device_num]
        )
        success, block_type_num = info_cmds.GetBlockTypeNum(self.device_list[device_num])

        if block_type_num == 48:
            return 96
        elif block_type_num == 49:
            return 384
        else:
            return -1

    def _login_user(self, device_num: int) -> None:
        """Login as admin user.

        Args:
            device_num: Device index
        """
        try:
            login_cmds = LoginOutCmds(
                ApplicationSettings.CommunicationSettings, self.device_list[device_num]
            )
            login_cmds.LoginUser(
                self.device_list[device_num],
                UserInitials("ADM"),
                UserPassword("Admin"),
            )
            self.logger.log("User logged in")
        except Exception as e:
            # User may already be logged in
            self.logger.log(f"Login attempt: {e}")

    def run_protocol(self, plate_type: int, program: int) -> None:
        """Run a PCR protocol.

        Args:
            plate_type: Plate type (96 or 384)
            program: Program number to run
        """
        device_num = self.connect_device(plate_type)

        try:
            self.logger.log(f"Starting program {program} on device {device_num}")

            # Start the program
            block_cmds = BlockCmds(
                ApplicationSettings.CommunicationSettings, self.device_list[device_num]
            )
            block_cmds.StartProgramOnBlock(
                self.device_list[device_num],
                UserInitials("ADM"),
                ProgramNumber(program, EnProgramType.TYPE_PROGRAM),
                BlockNumber(1),
                True,  # Start run log file
            )

            # Wait for completion
            time.sleep(10)  # Initial delay
            self._wait_until_ready(device_num)


        except Exception as e:
            print("ERROR")
            raise

    def open_lid(self, plate_type: int) -> None:
        """Open the thermocycler lid.

        Args:
            plate_type: Plate type (96 or 384)
        """
        device_num = self.connect_device(plate_type)

        try:

            block_cmds = BlockCmds(
                ApplicationSettings.CommunicationSettings, self.device_list[device_num]
            )
            block_cmds.OpenMotLid(self.device_list[device_num], BlockNumber(1))

            time.sleep(25)  # Wait for lid to open

        except Exception as e:
            print("ERROR")
            raise

    def close_lid(self, plate_type: int) -> None:
        """Close the thermocycler lid.

        Args:
            plate_type: Plate type (96 or 384)
        """
        device_num = self.connect_device(plate_type)

        try:
            block_cmds = BlockCmds(
                ApplicationSettings.CommunicationSettings, self.device_list[device_num]
            )
            block_cmds.CloseMotLid(self.device_list[device_num], BlockNumber(1))

            time.sleep(25) 
        except Exception as e:
            print("ERROR")
            raise

    def get_status(self, plate_type: int) -> dict:
        """Get the current status of the thermocycler.

        Args:
            plate_type: Plate type (96 or 384)

        Returns:
            Dictionary with status information
        """
        device_num = self.connect_device(plate_type)
        print("ONE")

        try:
            print("TWO")
            is_active = self._get_state(device_num)
            print("THREE")
            status_msg = "block running" if is_active else "block free"
            print(status_msg)

            return {
                "is_active": is_active,
                "status": status_msg,
            }

        except Exception as e:
            print("ERROR")
            raise

    def _get_state(self, device_num: int) -> bool:
        """Get the state of the thermocycler block.

        Args:
            device_num: Device index

        Returns:
            True if block is active, False otherwise
        """
        tcda_cmds = TcdaCmds(
            ApplicationSettings.CommunicationSettings, self.device_list[device_num]
        )
        result, block_state = tcda_cmds.GetBlockState(
            self.device_list[device_num], BlockNumber(1)
        )

        return block_state.ActiveBlock

    def _get_lid_state(self, device_num: int) -> str:
        """Get the state of the thermocycler lid.

        Args:
            device_num: Device index

        Returns:
            "open", "closed", or "busy"
        """
        try:
            tcda_cmds = TcdaCmds(
                ApplicationSettings.CommunicationSettings, self.device_list[device_num]
            )
            result, lid_state_list = tcda_cmds.GetMotLidState(self.device_list[device_num])

            lid_state = str(lid_state_list)

            if lid_state == "0000 0000 0000 0011;;":
                return "open"
            elif lid_state == "0000 0000 0000 0101;;":
                return "closed"
            else:
                return "busy"

        except Exception as e:
            print("ERROR")
            return "error"

    def _check_clear(self, device_num: int) -> int:
        """Check if device is clear and ready.

        Args:
            device_num: Device index

        Returns:
            0 if ready, 1 if waiting, -1 on error
        """
        # Check if device is running
        is_active = self._get_state(device_num)
        if is_active:
            self.logger.log("Protocol still in progress, waiting...")
            time.sleep(5)
            return 1

        # Check lid state
        lid_status = self._get_lid_state(device_num)
        if lid_status == "busy":
            self.logger.log("Lid not open or closed, waiting...")
            time.sleep(10)
            return 1

        if lid_status == "closed":
            self.logger.log("Lid is closed, opening...")
            self.open_lid_direct(device_num)
            time.sleep(10)
            return 1

        # Lid is open and block is not active
        return 0

    def _wait_until_ready(self, device_num: int) -> None:
        """Wait until the device is ready.

        Args:
            device_num: Device index
        """
        plate_status = 1
        while plate_status == 1:
            plate_status = self._check_clear(device_num)
            if plate_status == -1:
                raise RuntimeError("Error waiting for device to be ready")
            time.sleep(5)

        if plate_status == 0:
            self.logger.log("Plate ready to be retrieved")
        else:
            raise RuntimeError("Unknown plate status")

    def open_lid_direct(self, device_num: int) -> None:
        """Open lid without connecting (internal use).

        Args:
            device_num: Device index
        """
        block_cmds = BlockCmds(
            ApplicationSettings.CommunicationSettings, self.device_list[device_num]
        )
        block_cmds.OpenMotLid(self.device_list[device_num], BlockNumber(1))

    def get_temperature(self, plate_type: int) -> dict:
        """Get temperature readings.

        Args:
            plate_type: Plate type (96 or 384)

        Returns:
            Dictionary with temperature readings
        """
        device_num = self.connect_device(plate_type)

        try:
            tcda_cmds = TcdaCmds(
                ApplicationSettings.CommunicationSettings, self.device_list[device_num]
            )

            # Get lid temperature
            success, lid_temp = tcda_cmds.GetHeatedLidTemp(
                self.device_list[device_num], BlockNumber(1)
            )

            # Get block temperatures
            success, left_temp = tcda_cmds.GetBlockTempLeft(
                self.device_list[device_num], BlockNumber(1)
            )
            success, right_temp = tcda_cmds.GetBlockTempRight(
                self.device_list[device_num], BlockNumber(1)
            )
            success, middle_temp = tcda_cmds.GetBlockTempMiddle(
                self.device_list[device_num], BlockNumber(1)
            )

            return {
                "lid": str(lid_temp),
                "left": str(left_temp),
                "right": str(right_temp),
                "middle": str(middle_temp),
            }

        except Exception as e:
            self.logger.log_error(f"Error getting temperature: {e}")
            raise

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.device_list = None
            GC.Collect()
            GC.WaitForPendingFinalizers()
            gc.collect()
        except Exception:
            pass


if __name__ == "__main__":
    biometra = BiometraInterface()
    # biometra.connect_device(96)
    # biometra.close_lid(96)
    biometra.get_status(96)
