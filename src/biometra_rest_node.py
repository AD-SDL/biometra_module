"""REST-based node for Biometra Thermocycler device"""

from typing import Annotated

from madsci.common.types.node_types import RestNodeConfig
from madsci.common.types.resource_types import Slot
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode

from biometra_interface import BiometraInterface

from madsci.client.event_client import EventClient

import time


class BiometraNodeConfig(RestNodeConfig):
    """Configuration for the Biometra node."""

    device_port: int = 2002


class BiometraNode(RestNode):
    """A node to control the Biometra thermocycler device."""

    biometra: BiometraInterface = None
    config_model = BiometraNodeConfig
    config: BiometraNodeConfig = BiometraNodeConfig()
    module_version = "1.0.0"

    def __init__(self) -> None:
        """Initializes the Biometra node."""
        super().__init__()

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        self.init_resource_templates()
        self.create_resources()

        # self.biometra = BiometraInterface(
        #     device_port=self.config.device_port,
        #     protocol = self.protocol,
        #     logger=self.logger,
        # )
        self.biometra = BiometraInterface(
            logger=self.logger,
        )
        self.device_num = self.biometra.connect_device(96)
        #make sure open?
        # self.biometra.open()

    def init_resource_templates(self) -> None:
        """Initialize resource templates used by this node module."""

        self.resource_client.create_template(
            resource=Slot(
                resource_class="biometra_thermocycler_nest",
                resource_description="The nest where plates are placed for thermocycling",
            ),
            template_name="biometra_thermocycler_nest",
            description="Template for Biometra thermocycler nest",
            tags=["PlateNest", "ANSI/SLAS"],
        )

    def create_resources(self) -> None:
        """Create resources used by this node."""
        self.thermocycler_nest = self.resource_client.create_resource_from_template(
            "biometra_thermocycler_nest",
            resource_name=f"{self.node_definition.node_name}_plate_nest",
        )

    def shutdown_handler(self) -> None:
        """Called to close connections to devices or clean up any other resources."""
        try:
            if self.biometra:
                del self.biometra
                self.biometra = None
        except Exception as err:
            self.logger.log_error(f"Error shutting down the Biometra Node: {err}")

    def state_handler(self) -> None:
        """Periodically checks the state of the Biometra device and updates the node's state."""
        if self.biometra:
            status = self.biometra.get_status(96) #TODO: un hard code
        else:
            self.logger.log_error("Biometra interface is not initialized")
        #     return

        # self.node_state["status_message"] = self.biometra.ready_message.model_dump(
        #     mode="json"
        # )

    @action(name="run_protocol")
    def run_protocol(
        self,
        plate_type: Annotated[int, "Plate type definition (96 or 384)"],
        program: Annotated[int, "Program number identifier for the protocol to run"],
    ) -> None:
        """Run a PCR protocol on the thermocycler."""
        self.biometra.run_protocol(plate_type=plate_type, program=program)

    @action(name="open_lid")
    def open_lid(
        self,
        plate_type: Annotated[int, "Plate type definition (96 or 384)"],
    ) -> None:
        """Open the thermocycler lid."""
        """check current state"""
        curr_state = self.biometra._get_lid_state(device_num=self.device_num)
        print(curr_state)
        if curr_state == "open":
            self.logger.log("Biometra is already open")
        elif curr_state == "closed":
            self.logger.log("Biometra is opening")
            self.biometra.open_lid(plate_type=plate_type)
        # pause for 25 seconds, allow for lid to open
        time.sleep(25)
        # while self.biometra._get_lid_state(device_num=self.device_num) == "busy":
        #     self.logger.log("Biometra is opening")
        #     time.sleep(5)
        if self.biometra._get_lid_state(device_num=self.device_num) == "open":
            self.logger.log("Biometra is open")
        elif self.biometra._get_lid_state(device_num=self.device_num) == "closed":
            self.logger.log_error("Biometra is still closed")
        # time.sleep(25)


    @action(name="close_lid")
    def close_lid(
        self,
        plate_type: Annotated[int, "Plate type definition (96 or 384)"],
    ) -> None:
        """Close the thermocycler lid."""
        """check current state"""
        curr_state = self.biometra._get_lid_state(device_num=self.device_num)
        if curr_state == "closed":
            self.logger.log("Biometra is already closed")
        elif curr_state == "open":
            self.logger.log("Biometra is closing")
            self.biometra.close_lid(plate_type=plate_type)
        # pause for 25 seconds, allow for lid to open
        time.sleep(25)
        # while self.biometra._get_lid_state(device_num=self.device_num) == "busy":
        #     self.logger.log("Biometra is closing")
        #     time.sleep(5)
        if self.biometra._get_lid_state(device_num=self.device_num) == "closed":
            self.logger.log("Biometra is closed")
        elif self.biometra._get_lid_state(device_num=self.device_num) == "open":
            self.logger.log_error("Biometra is still open")
        # self.biometra.close_lid(plate_type=plate_type)
        # pause for 25 seconds, allow for lid to open
        # time.sleep(25)


    # @action(name="get_status")
    # def get_status(
    #     self,
    #     plate_type: Annotated[int, "Plate type definition (96 or 384)"],
    # ) -> str:
    #     """Get the current status of the thermocycler."""
    #     result = self.biometra.get_device_status(plate_type=plate_type)
    #     return result.get("action_msg", "")


if __name__ == "__main__":
    biometra_node = BiometraNode()
    biometra_node.start_node()
