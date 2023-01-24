from src.rwkvMaster import RWKVMaster
from src.agnostic.samplers.numpy import npsample


def initTorchScriptFile(Path):
    import torch
    embed = Path.split("-")[2].split(".")[0]
    layers = Path.split("-")[1]
    mymodel = torch.jit.load(Path)
    device = torch.device("cuda" if "gpu" in Path else "cpu")
    dtype = torch.bfloat16 if "bfloat16" in Path else torch.float32 if "float32" in Path else torch.float16 if "float16" in Path else torch.float64
    print("input shape", dtype)

    class InterOp():
        def forward(self, x, y):

            mm, nn = mymodel(torch.LongTensor(x), y)

            return mm.cpu(), nn
    model = InterOp()
    emptyState = torch.tensor(
        [[0.01]*int(embed)]*int(layers)*5, dtype=dtype, device=device)

    def initTensor(x): return torch.tensor(x, dtype=dtype, device=device)

    useSampler = "sampler" not in Path

    return RWKVMaster(model, emptyState, initTensor, npsample if useSampler else None)
