"""REST-based node for Biometra Thermocycler device"""

import time
from typing import Annotated, ClassVar

from madsci.common.types.node_types import (
    NodeIntrinsicLocationDefinition,
    NodeRepresentationTemplateDefinition,
    RestNodeConfig,
)
from madsci.common.types.resource_types import Slot
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode

from biometra_interface import BiometraInterface


class BiometraNodeConfig(RestNodeConfig):
    """Configuration for the Biometra node."""

    device_port: int = 2002


class BiometraNode(RestNode):
    """A node to control the Biometra thermocycler device."""

    biometra: BiometraInterface = None
    config_model = BiometraNodeConfig
    config: BiometraNodeConfig = BiometraNodeConfig()
    module_version = "1.0.0"

    # Location representation templates — registered automatically by template_handler()
    location_representation_templates: ClassVar[
        list[NodeRepresentationTemplateDefinition]
    ] = [
        NodeRepresentationTemplateDefinition(
            template_name="biometra_nest_repr",
            default_values={"carriage_type": "standard", "capacity": 1},
            schema_def={
                "type": "object",
                "properties": {
                    "capacity": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Number of plates the nest can hold",
                    },
                },
            },
            required_overrides=[],
            tags=["thermocycler", "nest", "plate_nest"],
            version="1.0.0",
            description="Biometra TRobot II nest representation with capacity",
        ),
    ]
    # Intrinsic locations — auto-created on startup with '{node_name}.' prefix
    intrinsic_locations: ClassVar[list[NodeIntrinsicLocationDefinition]] = [
        NodeIntrinsicLocationDefinition(
            location_name="biometra_nest",
            description="Biometra nest where plates are placed for thermocycling.",
            representation_template_name="biometra_nest_repr",
            resource_template_name="biometra.nest",
            allow_transfers=True,
        ),
    ]

    def __init__(self) -> None:
        """Initializes the Biometra node."""
        super().__init__()

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        self.init_resource_templates()
        self.create_resources()

        self.biometra = BiometraInterface(
            logger=self.logger,
        )
        self.device_num = self.biometra.connect_device(96)

    def init_resource_templates(self) -> None:
        """Initialize resource templates used by this node module."""

        self.resource_client.create_template(
            resource=Slot(
                resource_description="The nest where PCR plates are placed for thermocycling.",
            ),
            template_name="biometra.nest",
            description="Template for Biometra thermocycler nest",
            tags=["PlateNest", "ANSI/SLAS"],
        )

    def create_resources(self) -> None:
        """Create resources used by this node."""
        self.thermocycler_nest = self.resource_client.create_resource_from_template(
            "biometra.nest",
            resource_name=f"{self.node_info.node_name}.nest",
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
            status = self.biometra.get_status(96)  # TODO: un hard code
        else:
            self.logger.log_error("Biometra interface is not initialized")


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
        elif curr_state == "busy":
            time.sleep(25)
            if self.biometra._get_lid_state(device_num=self.device_num) == "busy":
                self.logger.log("Biometra stuck in busy state, opening")
                self.biometra.open_lid(plate_type=plate_type)
        # pause for 25 seconds, allow for lid to open
        time.sleep(25)
        if self.biometra._get_lid_state(device_num=self.device_num) == "open":
            self.logger.log("Biometra is open")
        elif self.biometra._get_lid_state(device_num=self.device_num) == "closed":
            self.logger.log_error("Biometra is still closed")

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
        elif curr_state == "busy":
            time.sleep(25)
            if self.biometra._get_lid_state(device_num=self.device_num) == "busy":
                self.logger.log("Biometra stuck in busy state, closing")
                self.biometra.close_lid(plate_type=plate_type)
        # pause for 25 seconds, allow for lid to open
        time.sleep(25)
        if self.biometra._get_lid_state(device_num=self.device_num) == "closed":
            self.logger.log("Biometra is closed")
        elif self.biometra._get_lid_state(device_num=self.device_num) == "open":
            self.logger.log_error("Biometra is still open")




if __name__ == "__main__":
    biometra_node = BiometraNode()
    biometra_node.start_node()
