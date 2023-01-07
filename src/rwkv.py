
import torch
from src.rwkvops import RwkvOpList as Backends

import torch
import gc
from typing import Dict
from tqdm import tqdm
import inquirer
import os


def RWKV(Path=None, mode=None, *args, **kwargs):

    if (Path == None):
        files = os.listdir()
        # filter by ending in .pth
        files = [f for f in files if f.endswith(
            ".pth") or f.endswith(".pt") or f.endswith(".tflite")]

        questions = [
            inquirer.List('file',
                          message="What model do you want to use?",
                          choices=files,
                          )]
        Path = inquirer.prompt(questions)["file"]

    if (mode == None and Path.endswith(".pth")):
        mode = inquirer.prompt([inquirer.List('mode',
                                              message="What inference backend do you want to use?",
                                              choices=Backends.keys(),
                                              )])["mode"]

    elif Path.endswith(".pt"):
        embed = Path.split("-")[2].split(".")[0]
        layers = Path.split("-")[1]
        model = torch.jit.load(Path)
        device = torch.device("cuda" if "gpu" in Path else "cpu")
        dtype = torch.bfloat16 if "bfloat16" in Path else torch.float32 if "float32" in Path else torch.float16 if "float16" in Path else torch.float64
        print("input shape", dtype)

        class InterOp():
            def forward(self, x, y):

                mm, nn = model(torch.LongTensor(x), y)

                return mm.cpu(), nn
        return InterOp(), torch.tensor([[0.01]*int(embed)]*int(layers)*5, dtype=dtype, device=device)

    elif Path.endswith(".tflite"):
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
        return InterOp(), tf.convert_to_tensor([[0.01]*int(embed)]*int(layers), dtype=dtype)

    n_layer = 0

    with torch.no_grad():
        w: Dict[str, torch.Tensor] = torch.load(
            Path, map_location="cpu")
        # refine weights and send to correct device
        keys = list(w.keys())
        for x in keys:
            if '.time_' in x:
                w[x] = w[x].squeeze()

            if '.time_decay' in x:
                w[x] = torch.exp(-torch.exp(w[x].double())
                                 ).to(dtype=torch.bfloat16)

            if 'receptance.weight' in x:
                w[x] = -w[x]

            w[x].requires_grad = False
            w[x] = w[x].to(dtype=torch.bfloat16)
            try:
                if (int(x.split('.')[1])+1 > n_layer):
                    n_layer = int(x.split('.')[1])+1
            except:
                pass

    # store weights in self.w

        keys = list(w.keys())

        preprocess = []
        for x in tqdm(range(len(w["emb.weight"]))):
            preprocess = preprocess + [torch.layer_norm(w["emb.weight"][x], (w["blocks.0.ln0.weight"].shape[0],),
                                                        weight=w["blocks.0.ln0.weight"], bias=w["blocks.0.ln0.bias"])]

    gc.collect()
    torch.cuda.empty_cache()

    ops = Backends[mode](
        n_layer, len(w[f"blocks.0.ffn.time_mix_k"]), *args, **kwargs)

    class RWKVTFLayer(ops.module):
        def __init__(self, x):
            super(RWKVTFLayer, self).__init__()

            self.i = x

            self.ln1w = ops.initTensor(w[f"blocks.{x}.ln1.weight"])
            self.ln1b = ops.initTensor(w[f"blocks.{x}.ln1.bias"])
            self.ln2w = ops.initTensor(w[f"blocks.{x}.ln2.weight"])
            self.ln2b = ops.initTensor(w[f"blocks.{x}.ln2.bias"])
            self.time_decay = ops.initTensor(w[f"blocks.{x}.att.time_decay"])
            self.time_first = ops.initTensor(w[f"blocks.{x}.att.time_first"])
            self.kktk = ops.initTensor(w[f"blocks.{x}.att.time_mix_k"])
            self.vvtv = ops.initTensor(w[f"blocks.{x}.att.time_mix_v"])
            self.rrtr = ops.initTensor(w[f"blocks.{x}.att.time_mix_r"])
            self.key = ops.initTensor(w[f"blocks.{x}.att.key.weight"])
            self.value = ops.initTensor(w[f"blocks.{x}.att.value.weight"])
            self.receptance = ops.initTensor(
                w[f"blocks.{x}.att.receptance.weight"])
            self.outputvv = ops.initTensor(
                w[f"blocks.{x}.att.output.weight"])
            self.time_mix_k_ffn = ops.initTensor(
                w[f"blocks.{x}.ffn.time_mix_k"])
            self.time_mix_r_ffn = ops.initTensor(
                w[f"blocks.{x}.ffn.time_mix_r"])
            self.key_ffn = ops.initTensor(w[f"blocks.{x}.ffn.key.weight"])
            self.receptance_ffn = ops.initTensor(
                w[f"blocks.{x}.ffn.receptance.weight"])
            self.value_ffn = ops.initTensor(
                w[f"blocks.{x}.ffn.value.weight"])

        @ ops.layerdef
        def forward(self, x, statea, stateb, statec, stated):
            xy = ops.layernorm(x, self.ln1w, self.ln1b)

            kk = ops.matvec(
                self.key, ops.lerp(statea, xy, self.kktk))

            v = ops.matvec(self.value, ops.lerp(statea, xy, self.vvtv))

            r = ops.logistical(ops.matvec(
                self.receptance, ops.lerp(statea, xy, self.rrtr)))

            kt = ops.exp(ops.minimum(
                kk + self.time_first, ops.klimit))
            k = ops.exp(ops.minimum(kk, ops.klimit))

            wrd = ((stateb + kt*v)/(statec + kt))
            outb = (stateb + k*v) * self.time_decay
            outc = (statec + k) * self.time_decay

            mvv = x + ops.matvec(self.outputvv, r*wrd)

            ddd = ops.layernorm(mvv, self.ln2w, self.ln2b)

            km = ops.relu(ops.matvec(self.key_ffn, ops.lerp(
                stated, ddd, self.time_mix_k_ffn)))

            rt = ops.logistical(ops.matvec(self.receptance_ffn, ops.lerp(
                stated, ddd, self.time_mix_r_ffn)))

            x = mvv + ops.matvec(self.value_ffn, km*km)*rt

            return x, xy, outb, outc, ddd

    class RWKVTFPre(ops.module):
        def __init__(self):
            super(RWKVTFPre, self).__init__()
            self.preprocess = ops.stack(
                list(map(ops.initCpuTensor, preprocess)))

        @ ops.prefunc
        def forward(self, x):
            # invert x to be reversed,
            return self.preprocess[x[-1]]
    matvec = ops.matvec
    layernorm = ops.layernorm

    class RWKVTFPost(ops.module):
        def __init__(self):
            super(RWKVTFPost, self).__init__()

            self.postprocess0 = ops.initCpuTensor(w["ln_out.weight"])
            self.postprocess1 = ops.initCpuTensor(w["ln_out.bias"])
            self.postprocess2 = ops.initCpuTensor(w["head.weight"])

        @ ops.postfunc
        def forward(self, x):

            return matvec(self.postprocess2, layernorm(x, self.postprocess0,
                                                       self.postprocess1))

    class myRWKV(ops.module):
        @ ops.initfunc
        def __init__(self):
            super(myRWKV, self).__init__()
            self.preprocess = RWKVTFPre()
            self.ops = ops

            for i in range(n_layer):
                self.__dict__[f"layer{i}"] = RWKVTFLayer(i)

            self.postprocess = RWKVTFPost()

        @ ops.mainfunc
        def forward(self, x, state=None):

            # profile usage
            # print("start", len(self.mylayers))

            # with torch.profiler.profile(record_shapes=True, use_cuda=True) as prof:

            if (state is None):
                state = ops.emptyState

            x = self.preprocess.forward(x)

            statea = state[0::4]
            stateb = state[1::4]
            statec = state[2::4]
            stated = state[3::4]

            ot = []

            # print("start", len(self.mylayers))

            for i in range(n_layer):
                x, aaa, bbb, ccc, ddd = self.__dict__[f"layer{i}"].forward(
                    x, statea[i], stateb[i], statec[i], stated[i])
                ot = ot + [aaa, bbb, ccc, ddd]

            x = self.postprocess.forward(x)
            # print(len(ot))

            # display usage

            # print(prof.key_averages().table(
            #     sort_by="cuda_time_total", row_limit=10, top_level_events_only=True))
            # exit()
            return x, ops.stack(ot)
    return ops.postProcessModule(myRWKV()), ops.emptyState
