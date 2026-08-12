using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Assets;
using CUE4Parse.UE4.Assets.Exports.Animation;
using CUE4Parse.UE4.Versions;
using CUE4Parse_Conversion;
using CUE4Parse_Conversion.Options;

if (args.Length < 2)
{
    Console.Error.WriteLine("Usage: Extractor <unreal_source_dir> <output_dir>");
    return 2;
}

var sourceDir = Path.GetFullPath(args[0]);
var outputDir = Path.GetFullPath(args[1]);
Directory.CreateDirectory(outputDir);

Console.WriteLine($"Scanning UE5.5 loose assets: {sourceDir}");
var provider = new DefaultFileProvider(
    sourceDir,
    SearchOption.AllDirectories,
    true,
    new VersionContainer(EGame.GAME_UE5_5));
provider.Initialize();
Console.WriteLine($"Provider indexed {provider.Files.Count} files.");
Console.WriteLine($"Provider project name: {provider.ProjectName}");
foreach (var dependencyPath in new[]
{
    "/Game/FP_AKS74U_Animation/Demo/FirstPersonArms/Character/Mesh/SKEL_UE5_Mannequin_Arms",
    "/Game/FP_AKS74U_Animation/AKS74U/Meshes/SK_AK74U_Skeleton"
})
{
    Console.WriteLine($"DEPENDENCY {(provider.TryGetGameFile(dependencyPath, out var dep) ? "OK" : "MISSING")} {dependencyPath} => {(dep?.Path ?? "-")}");
}

bool WantedPackage(string fileId)
{
    if (!fileId.EndsWith(".uasset", StringComparison.OrdinalIgnoreCase)) return false;
    var normalized = fileId.Replace('\\', '/');
    var name = Path.GetFileNameWithoutExtension(normalized);
    return normalized.Contains("/AKS74U/Animations/", StringComparison.OrdinalIgnoreCase)
        && (name.StartsWith("A_FP_", StringComparison.OrdinalIgnoreCase) || name.StartsWith("A_WBP_", StringComparison.OrdinalIgnoreCase));
}

// We intentionally export ONLY UAnimSequence assets now. The loose editor
// skeletal meshes may not expose cooked RenderData LOD payloads to CUE4Parse.
// We do not depend on direct mesh export for this lab: the site uses fallback
// browser GLBs and retargets the real AKS-74U PSA tracks onto them.
var session = new ExportSession { MaxDegreeOfParallelism = 2 };
var loadedPackages = 0;
var queued = 0;
var failures = new List<string>();

foreach (var entry in provider.Files.Where(kvp => WantedPackage(kvp.Key)).OrderBy(kvp => kvp.Key))
{
    var fileId = entry.Key;
    var gameFile = entry.Value;
    try
    {
        IPackage package = provider.LoadPackage(gameFile);
        var objects = package.GetExports();
        loadedPackages++;
        foreach (var obj in objects)
        {
            if (obj is UAnimSequence)
            {
                session.Add(obj);
                queued++;
                Console.WriteLine($"QUEUE {obj.GetType().Name,-22} {obj.Name}  [{fileId}]");
            }
        }
    }
    catch (Exception ex)
    {
        failures.Add($"{fileId}: {ex.GetType().Name}: {ex.Message}");
        Console.WriteLine($"WARN load failed: {fileId}: {ex}");
    }
}

Console.WriteLine($"Loaded {loadedPackages} animation packages; queued {queued} sequences.");
if (!session.HasQueuedItems)
{
    Console.Error.WriteLine("No animation sequences were queued.");
    return 3;
}

var options = new ExportOptions(meshFormat: EMeshFormat.ActorX, exportMaterials: false, exportMorphTargets: false);
var results = await session.RunAsync(outputDir, options);
var successCount = results.Count(r => r.Success);
Console.WriteLine($"Animation export results: {successCount}/{results.Count} successful.");
foreach (var result in results)
{
    var paths = string.Join(", ", result.DiskFilePaths ?? Array.Empty<string>());
    if (result.Success)
        Console.WriteLine($"OK {result.ObjectPath} => {paths}");
    else
    {
        Console.WriteLine($"FAIL {result.ObjectPath}");
        Console.WriteLine(result.Error?.ToString() ?? "  (CUE4Parse returned no exception details)");
    }
}

var psaCount = results
    .Where(r => r.Success && r.DiskFilePaths is not null)
    .SelectMany(r => r.DiskFilePaths!)
    .Count(path => path.EndsWith(".psa", StringComparison.OrdinalIgnoreCase));
Console.WriteLine($"ActorX animations written: {psaCount}");

if (failures.Count > 0)
{
    Console.WriteLine("Package load warnings:");
    foreach (var failure in failures) Console.WriteLine("  " + failure);
}
return psaCount > 0 ? 0 : 4;
