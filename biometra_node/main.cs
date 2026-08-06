using BiometraLibrary.DeviceExtComClasses.SystemClasses.InfoClasses.InfoDataClasses;
using BiometraLibrary.HelperClasses.ListHelperClasses;
using Grapevine;
using McMaster.Extensions.CommandLineUtils;

namespace biometra_node
{
    public class Biometra
    {

        public static int Main(string[] args) => CommandLineApplication.Execute<Biometra>(args);

        [Option(Description = "Server Port")]
        public int Port { get; } = 2008;
        [Option(Description = "Device ID")]
        public int Id { get; } = 0;
        [Option(Description = "Device Name (for logging)")]
        public string Name { get; } = "HiG4 Centrifuge";
        [Option(Description = "Whether or not to simulate the device")]
        public bool Simulate { get; } = false;

        public string state = ModuleStatus.IDLE;
        private IRestServer server;
        AdvancedList<DeviceDescription> device_list;

        [System.Diagnostics.CodeAnalysis.SuppressMessage("CodeQuality", "IDE0051:Remove unused private members", Justification = "Used by CommandLineApplication.Execute above")]
        private void OnExecute()
        {

            InitializeBiometra();
            server = RestServerBuilder.UseDefaults().Build();
            server.Prefixes.Add("http://+:" + Port.ToString() + "/");
            server.Locals.TryAdd("device_list", device_list);
            server.Locals.TryAdd("state", state);
            server.Start();

            Console.WriteLine("Press enter to stop the server");
            Console.ReadLine();

            server.Stop();
        }

        private void InitializeBiometra()
        {
            device_list = Biometra_Functions.FindDevices();
        }
    }
}
