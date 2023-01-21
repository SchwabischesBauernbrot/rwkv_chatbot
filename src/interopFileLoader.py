from src.rwkvMaster import RWKVMaster
from src.rwkvops import RWKVOPS, RWKVPTOps, npsample, torchsample


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


def initTFLiteFile(Path):
    import tensorflow.lite as tflite

    import tensorflow as tf

    interpreter = tflite.Interpreter(
        model_path=Path)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    embed = input_details[1]['shape'][1]
    layers = input_details[1]['shape'][0]
    dtype = input_details[1]['dtype']

    class InterOp():
        def forward(self, x, y):

            interpreter.set_tensor(
                input_details[0]['index'], tf.convert_to_tensor(x, dtype=tf.int32))
            interpreter.set_tensor(
                input_details[1]['index'], y)
            interpreter.invoke()
            output_data = interpreter.get_tensor(
                output_details[0]['index']), interpreter.get_tensor(output_details[1]['index'])

            return output_data
    model = InterOp()
    emptyState = tf.convert_to_tensor(
        [[0.01]*int(embed)]*int(layers), dtype=dtype)

    def initTensor(x): return tf.convert_to_tensor(x, dtype=dtype)
    return RWKVMaster(model, emptyState, initTensor, npsample)
