using BiometraLibrary.DeviceExtComClasses.SystemClasses.InfoClasses.InfoDataClasses;
using BiometraLibrary.HelperClasses.ListHelperClasses;
using Grapevine;
using Newtonsoft.Json;

namespace biometra_node
{
    [RestResource]
    public class BiometraRestServer
    {
        private readonly IRestServer _server;

        public BiometraRestServer(IRestServer server)
        {
            _server = server;
        }

        [RestRoute("Get", "/state")]
        public async Task State(IHttpContext context)
        {
            string state = _server.Locals.GetAs<string>("state");
            Dictionary<string, string> response = new Dictionary<string, string>
            {
                ["State"] = state
            };
            await context.Response.SendResponseAsync(JsonConvert.SerializeObject(response));
        }

        [RestRoute("Get", "/about")]
        public async Task About(IHttpContext context)
        {
            object? module_about = JsonConvert.DeserializeObject(/*lang=json*/ @"
                {
                    ""name"":""Biometra"",
                    ""model"":""Analytik Jena Biometra TRobot II"",
                    ""interface"":""wei_rest_node"",
                    ""version"":""0.1.0"",
                    ""description"":""Module for automating a Biometra thermocycler."",
                    ""actions"": [
                        {
                            ""name"":""run_protocol"",
                            ""args"":[
                                {
                                    ""name"":""plate_type"",
                                    ""type"":""int"",
                                    ""default"":null,
                                    ""required"":true,
                                    ""description"":""Plate Type Definition.""
                                },
                                {
                                    ""name"":""program"",
                                    ""type"":""int"",
                                    ""default"":null,
                                    ""required"":true,
                                    ""description"":""An identifier for the protocol to be run.""
                                },
                            ],
                            ""files"":[]
                        },
                        {
                            ""name"":""open_lid"",
                            ""args"":[
                                {
                                    ""name"":""plate_type"",
                                    ""type"":""int"",
                                    ""default"":null,
                                    ""required"":true,
                                    ""description"":""Plate Type Definition.""
                                },
                            ],
                            ""files"":[]
                        },
                        {
                            ""name"":""close_lid"",
                            ""args"":[
                                {
                                    ""name"":""plate_type"",
                                    ""type"":""int"",
                                    ""default"":null,
                                    ""required"":true,
                                    ""description"":""Plate Type Definition.""
                                },
                            ],
                            ""files"":[]
                        },
                        {
                            ""name"":""get_status"",
                            ""args"":[
                                {
                                    ""name"":""plate_type"",
                                    ""type"":""int"",
                                    ""default"":null,
                                    ""required"":true,
                                    ""description"":""Plate Type Definition.""
                                },
                            ],
                            ""files"":[]
                        },
                    ],
                    ""resource_pools"":[]
                }");
            await context.Response.SendResponseAsync((module_about is null) ? "{}" : module_about.ToString());
        }

        [RestRoute("Get", "/resources")]
        public async Task Resources(IHttpContext context)
        {
            // TODO
            await context.Response.SendResponseAsync("resources");
        }

        [RestRoute("Post", "/action")]
        public async Task Action(IHttpContext context)
        {

            Dictionary<string, string> result = UtilityFunctions.step_result();
            try
            {
                AdvancedList<DeviceDescription> device_list = _server.Locals.GetAs<AdvancedList<DeviceDescription>>("device_list");
                string state = _server.Locals.GetAs<string>("state");
                string? action_handle = context.Request.QueryString["action_handle"];
                string? action_vars = context.Request.QueryString["action_vars"];
                if (action_handle is null) { throw new Exception("No action_handle provided."); }
                if (action_vars is null) { throw new Exception("No action_vars provided."); }
                Dictionary<string, string>? args = JsonConvert.DeserializeObject<Dictionary<string, string>>(action_vars);
                if (args is null) { throw new Exception("Failed to parse arguments."); }

                int plate_type = Int32.Parse(args["plate_type"]);
                int device_num = Biometra_Functions.Connect(device_list, plate_type);

                if (state == ModuleStatus.BUSY)
                {
                    result = UtilityFunctions.step_result(StepStatus.FAILED, "", "Module is Busy");
                    await context.Response.SendResponseAsync(JsonConvert.SerializeObject(result));
                }

                UtilityFunctions.updateModuleStatus(_server, ModuleStatus.BUSY);
                switch (action_handle)
                {
                    case "run_protocol":
                        string prog = args["program"];
                        int prog_int = Int32.Parse(prog);
                        Biometra_Functions.run_program(device_list, prog_int, device_num);
                        System.Threading.Thread.Sleep(10000);
                        int plate_status = Biometra_Functions.wait_until_ready(device_list, device_num);
                        if (plate_status < 0) { throw new Exception($"Plate Status: {plate_status}"); }

                        result = UtilityFunctions.step_succeeded("Successfully ran protocol");
                        break;
                    case "open_lid":
                        Biometra_Functions.open_lid(device_list, device_num);
                        Thread.Sleep(25000);
                        //TODO: check if lid is closed, then check if its open
                        result = UtilityFunctions.step_succeeded("Opened lid");
                        break;
                    case "close_lid":
                        Biometra_Functions.close_lid(device_list, device_num);
                        System.Threading.Thread.Sleep(25000);
                        //TODO: check if lid is open, then check if its closed
                        result = UtilityFunctions.step_succeeded("Opened lid");
                        break;
                    case "get_status":
                        bool is_active = Biometra_Functions.get_state(device_list, device_num);
                        result = UtilityFunctions.step_succeeded(is_active ? "block running" : "block free");
                        break;
                    default:
                        result = UtilityFunctions.step_failed("Unknown action: " + action_handle);
                        break;
                }
                UtilityFunctions.updateModuleStatus(_server, ModuleStatus.IDLE);
            }
            catch (Exception ex)
            {
                UtilityFunctions.updateModuleStatus(_server, ModuleStatus.ERROR);
                result = UtilityFunctions.step_failed("Step failed: " + ex.ToString());
            }

            await context.Response.SendResponseAsync(JsonConvert.SerializeObject(result));
        }
    }
}
